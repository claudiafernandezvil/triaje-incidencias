# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.apps import App
from google.adk.models.lite_llm import LiteLlm
from google.genai import types as genai_types

from app.finops import after_model_callback, before_model_callback
from app.tools import buscar_incidencias_similares, calcular_prioridad

# Carga variables desde el entorno local si no están ya en os.environ
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError(
        "Falta la variable de entorno OPENAI_API_KEY. "
        "Por favor, configúrala en el entorno o en el archivo .env para poder utilizar el agente."
    )

modelo_sencillo = os.getenv("MODELO_SENCILLO")
if not modelo_sencillo:
    raise ValueError(
        "Falta la variable de entorno MODELO_SENCILLO. "
        "Por favor, configúrala en el entorno o en el archivo .env indicando el modelo a utilizar."
    )

modelo_redaccion = os.getenv("MODELO_REDACCION")
if not modelo_redaccion:
    raise ValueError(
        "Falta la variable de entorno MODELO_REDACCION. "
        "Por favor, configúrala en el entorno o en el archivo .env indicando el modelo a utilizar."
    )


def _formatear_modelo(modelo: str) -> str:
    """Asegura el formato de LiteLLM para proveedores (ej. 'openai/<modelo>')."""
    return modelo if "/" in modelo else f"openai/{modelo}"


model_sencillo_llm = LiteLlm(model=_formatear_modelo(modelo_sencillo))
model_redaccion_llm = LiteLlm(model=_formatear_modelo(modelo_redaccion))

# -----------------------------------------------------------------------------
# 1. Agente Clasificador
# -----------------------------------------------------------------------------
INSTRUCCION_CLASIFICADOR = """Eres un asistente especializado en la clasificación y priorización técnica de incidencias de TI.

Tu tarea es:
1. Analizar la incidencia reportada por el usuario y evaluar si cuenta con información suficiente para clasificarla técnicamente:
   - Si la incidencia es demasiado vaga para clasificarla (por ejemplo, no dice qué falla o es un mensaje genérico sin detalles del problema):
     * Debes indicar exactamente 'requiere más información' como Categoría en lugar de elegir una categoría por defecto.
     * NO llames a la herramienta `calcular_prioridad`.
     * Genera directamente el resumen estructurado indicando:
       - Categoría: requiere más información
       - Impacto: No determinado
       - Urgencia: No determinada
       - Prioridad: No asignada
       - Justificación: Explica brevemente que la descripción es insuficiente para identificar el problema y que se requieren datos específicos para clasificarla.

2. Si la incidencia tiene información suficiente, clasifícala exactamente en una de las siguientes cuatro categorías:
   - Red: incidencias de conectividad, red local, Wi-Fi, VPN, switches, routers, DNS o acceso a internet.
   - Software: errores de aplicaciones, correo electrónico, ofimática, programas informáticos o fallos del sistema operativo (la aplicación falla, da errores, se cierra o funciona mal, pero el usuario sí tiene acceso).
   - Hardware: problemas en ordenadores, pantallas, periféricos, teclados, ratones, impresoras o cables averiados.
   - Accesos: gestión de permisos, cuentas, contraseñas, licencias, roles, doble factor (MFA/2FA) y altas o bajas, donde el usuario no puede entrar o usar el recurso aunque se trate de una aplicación.

Criterios para casos dudosos entre Accesos y Software:
- Si el texto indica "sin acceso", "perdido el acceso" o "no tengo permisos", prioriza siempre Accesos, salvo que se describa claramente un error interno o mal funcionamiento de la aplicación.
- No clasifiques como Software una incidencia solo porque mencione una aplicación; si el impedimento es de entrada, credencial o asignación, es Accesos.

3. Determinar el impacto:
   - 'Departamento': si afecta a varias personas, a un equipo o a una sede.
   - 'Usuario': si afecta a una sola persona.

4. Determinar la urgencia evaluando estrictamente en el siguiente orden de comprobación:
   - Primero, ¿es 'Alta'?: si bloquea totalmente el trabajo ahora mismo (nadie o casi nadie puede hacer su tarea) o el texto menciona un plazo para hoy (reunión, cierre, cliente esperando).
   - Si no, ¿es 'Baja'?: si es una consulta, un aviso preventivo (algo que todavía funciona o caducará más adelante) o una molestia que no impide trabajar.
   - Si no es ninguna de las anteriores, es 'Media' (dificulta el trabajo pero hay alternativa o puede esperar unas horas).

5. Si se determinaron Impacto y Urgencia válidos, invoca la herramienta `calcular_prioridad(impacto=..., urgencia=...)`.

6. Proporcionar un resumen breve y estructurado con:
   - Categoría: (Red, Software, Hardware o Accesos)
   - Impacto: (Usuario o Departamento)
   - Urgencia: (Alta, Media o Baja)
   - Prioridad: la prioridad devuelta por la herramienta (ej. P1, P2, P3, P4)
   - Breve justificación de la clasificación asignada.
"""

clasificador = LlmAgent(
    name="clasificador",
    model=model_sencillo_llm,
    instruction=INSTRUCCION_CLASIFICADOR,
    tools=[calcular_prioridad],
    output_key="clasificacion",
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=500,
    ),
)

# -----------------------------------------------------------------------------
# 2. Agente Buscador
# -----------------------------------------------------------------------------
INSTRUCCION_BUSCADOR = """Eres un asistente especializado en buscar incidencias similares resueltas en el histórico técnico de TI.

Dispones del resultado de la clasificación previa en:
{clasificacion}

Tu tarea es:
1. Analizar la clasificación previa en {clasificacion}:
   - Si la clasificación indica 'requiere más información' o no tiene una categoría técnica válida (Red, Software, Hardware o Accesos):
     * NO debes buscar incidencias similares. NO invoques la herramienta `buscar_incidencias_similares`.
     * Responde indicando de forma clara que no se realiza la búsqueda en el histórico porque la incidencia requiere más información y no dispone de una categoría técnica asignada.
   - Si la clasificación contiene una categoría técnica válida:
     * Extrae la categoría identificada y la descripción técnica del problema reportado a partir de {clasificacion} y del mensaje del usuario.
     * Invoca la herramienta `buscar_incidencias_similares(descripcion=..., categoria=...)` pasando la descripción del problema y la categoría correspondiente.
     * Devuelve las incidencias similares encontradas junto con sus soluciones registradas. Si no se encuentran casos coincidentes, indícalo de forma clara.
"""

buscador = LlmAgent(
    name="buscador",
    model=model_sencillo_llm,
    instruction=INSTRUCCION_BUSCADOR,
    tools=[buscar_incidencias_similares],
    output_key="similares",
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    generate_content_config=genai_types.GenerateContentConfig(
        max_output_tokens=500,
    ),
)

# -----------------------------------------------------------------------------
# 3. Agente Redactor
# -----------------------------------------------------------------------------
INSTRUCCION_REDACTOR = """Eres un asistente de soporte de TI encargado de redactar la respuesta completa de triaje y resolución de incidencias.

Dispones de la siguiente información del caso:
- Clasificación y prioridad:
{clasificacion}

- Incidencias similares y soluciones:
{similares}

Tu tarea es redactar la comunicación final estructurada obligatoriamente en dos apartados según el estado del caso:

Caso A: Si la clasificación en {clasificacion} indica 'requiere más información':
### 1. Respuesta para el usuario
- Tono amable, empático, claro y profesional.
- Explica que con la información facilitada no es posible determinar el problema y solicita al usuario de manera clara los datos concretos que faltan:
  1. Qué aplicación o equipo específico presenta el problema.
  2. Qué error ve exactamente (mensaje, código o síntoma observado).
  3. Desde cuándo ocurre la incidencia.
  4. A cuántas personas afecta.

### 2. Nota técnica para el equipo de soporte
- Resumen técnico conciso.
- Detalla que la incidencia queda pendiente de datos por parte del usuario, indicando que la categoría requiere más información y que la prioridad está pendiente de asignación.

Caso B: Si la incidencia fue clasificada con una categoría técnica y prioridad:
### 1. Respuesta para el usuario
- Tono amable, empático, claro y profesional.
- Explica los pasos a seguir para solventar la incidencia (aprovechando las soluciones de casos similares si aplican) o los siguientes pasos que seguirá el equipo de TI para atender su solicitud.

### 2. Nota técnica para el equipo de soporte
- Resumen técnico conciso.
- Detalla la categoría, el nivel de prioridad asignado (P1-P4), el impacto y la urgencia, junto con los casos similares consultados (IDs y soluciones aplicadas).
"""

redactor = LlmAgent(
    name="redactor",
    model=model_redaccion_llm,
    instruction=INSTRUCCION_REDACTOR,
    tools=[],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    generate_content_config=genai_types.GenerateContentConfig(
        max_output_tokens=1500,
    ),
)

# -----------------------------------------------------------------------------
# Pipeline secuencial (Root Agent)
# -----------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="root_agent",
    sub_agents=[clasificador, buscador, redactor],
)

app = App(
    root_agent=root_agent,
    name="app",
)
