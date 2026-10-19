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
1. Analizar la incidencia reportada por el usuario y clasificarla exactamente en una de las siguientes cuatro categorías:
   - Red: incidencias de conectividad, red local, Wi-Fi, VPN, switches, routers, DNS o acceso a internet.
   - Software: errores de aplicaciones, correo electrónico, ofimática, programas informáticos o fallos del sistema operativo (la aplicación falla, da errores, se cierra o funciona mal, pero el usuario sí tiene acceso).
   - Hardware: problemas en ordenadores, pantallas, periféricos, teclados, ratones, impresoras o cables averiados.
   - Accesos: gestión de permisos, cuentas, contraseñas, licencias, roles, doble factor (MFA/2FA) y altas o bajas, donde el usuario no puede entrar o usar el recurso aunque se trate de una aplicación.

Criterios para casos dudosos entre Accesos y Software:
- Si el texto indica "sin acceso", "perdido el acceso" o "no tengo permisos", prioriza siempre Accesos, salvo que se describa claramente un error interno o mal funcionamiento de la aplicación.
- No clasifiques como Software una incidencia solo porque mencione una aplicación; si el impedimento es de entrada, credencial o asignación, es Accesos.

Ejemplos de referencia para casos dudosos:
- "El equipo de ventas no puede ingresar al portal comercial tras la renovación de licencias" -> Categoría: Accesos (imposibilidad de entrada por gestión de licencias/roles en una app).
- "El usuario entra al ERP pero la pantalla se congela y lanza un error al guardar una factura" -> Categoría: Software (el usuario puede entrar, pero la app falla internamente).
- "Varios analistas están bloqueados y no pueden autenticarse por fallo en el doble factor" -> Categoría: Accesos (bloqueo de autenticación/credenciales).

2. Determinar el impacto:
   - 'Usuario' si afecta a un único usuario.
   - 'Departamento' si afecta a un área, equipo o departamento entero.
3. Determinar la urgencia:
   - 'Alta', 'Media' o 'Baja' según la criticidad operativa y el bloqueo generado.
4. Invocar la herramienta `calcular_prioridad(impacto=..., urgencia=...)` con el impacto y la urgencia determinados.
5. Proporcionar un resumen breve y estructurado con:
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
)

# -----------------------------------------------------------------------------
# 2. Agente Buscador
# -----------------------------------------------------------------------------
INSTRUCCION_BUSCADOR = """Eres un asistente especializado en buscar incidencias similares resueltas en el histórico técnico de TI.

Dispones del resultado de la clasificación previa en:
{clasificacion}

Tu tarea es:
1. Extraer la categoría identificada y la descripción técnica del problema reportado a partir de {clasificacion} y del mensaje del usuario.
2. Invocar la herramienta `buscar_incidencias_similares(descripcion=..., categoria=...)` pasando la descripción del problema y la categoría correspondiente.
3. Devolver las incidencias similares encontradas junto con sus soluciones registradas. Si no se encuentran casos coincidentes, indícalo de forma clara.
"""

buscador = LlmAgent(
    name="buscador",
    model=model_sencillo_llm,
    instruction=INSTRUCCION_BUSCADOR,
    tools=[buscar_incidencias_similares],
    output_key="similares",
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

Tu tarea es redactar la comunicación final estructurada obligatoriamente en dos apartados:

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
