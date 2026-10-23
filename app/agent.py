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
from app.tickets import cerrar_ticket, consultar_tickets, registrar_incidencia, ver_ticket
from app.tools_consultas import estadisticas_historial
 
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
   - Únicamente si la incidencia no permite saber qué falla (por ejemplo, descripciones completamente vacías de detalles como un escueto "no funciona", sin indicar qué programa, dispositivo o síntoma se experimenta):
     * Debes indicar exactamente 'requiere más información' como Categoría en lugar de elegir una categoría por defecto.
     * Esta es la ÚNICA excepción en la que NO debes llamar a la herramienta `calcular_prioridad`.
     * Genera directamente el resumen estructurado indicando:
       - Categoría: requiere más información
       - Impacto: No determinado
       - Urgencia: No determinada
       - Prioridad: No asignada
       - Justificación: Explica brevemente que la descripción es insuficiente para identificar el problema y que se requieren datos específicos para clasificarla.
   - En todos los demás casos, la incidencia SÍ cuenta con información suficiente para clasificarla y priorizarla:
     * Las consultas y peticiones claras (por ejemplo, cómo cambiar una configuración o parámetro, solicitar la instalación de un programa o herramienta, o reportar un problema leve o aviso preventivo) SÍ tienen información suficiente y SIEMPRE necesitan prioridad y llamada a la herramienta.
 
2. Clasificar la incidencia con información suficiente exactamente en una de las siguientes cuatro categorías:
   - Red: incidencias de conectividad, red local, Wi-Fi, VPN, switches, routers, DNS o acceso a internet.
   - Software: errores de aplicaciones, correo electrónico, ofimática, programas informáticos o fallos del sistema operativo (la aplicación falla, da errores, se cierra o funciona mal, pero el usuario sí tiene acceso). También incluye peticiones de instalación o actualización de programas y aplicaciones, salvo que pidan explícitamente permisos o acceso de administrador.
   - Hardware: problemas en ordenadores, pantallas, periféricos, teclados, ratones, impresoras o cables averiados.
   - Accesos: gestión de permisos, cuentas, contraseñas, licencias, roles, doble factor (MFA/2FA) y altas o bajas, donde el usuario no puede entrar o usar el recurso aunque se trate de una aplicación.
 
Criterios para casos dudosos entre Accesos y Software:
- Las peticiones de instalación o adición de programas son Software, salvo que pidan explícitamente permisos o acceso de administrador.
- Si el texto indica "sin acceso", "perdido el acceso" o "no tengo permisos", prioriza siempre Accesos, salvo que se describa claramente un error interno o mal funcionamiento de la aplicación.
- No clasifiques como Software una incidencia solo porque mencione una aplicación; si el impedimento es de entrada, credencial o asignación, es Accesos.
 
3. Determinar el impacto:
   - 'Usuario': si el texto no menciona a otras personas, a un equipo o a una sede (incluso si el servicio o recurso afectado es compartido o corporativo, si no se menciona expresamente a más personas afectadas, el impacto es 'Usuario').
   - 'Departamento': únicamente si el texto menciona de forma explícita a varias personas, a un equipo o a una sede.
 
4. Determinar la urgencia evaluando estrictamente en el siguiente orden de comprobación:
   - Primero, ¿es 'Alta'?: únicamente si bloquea totalmente el trabajo ahora mismo (nadie o casi nadie puede hacer su tarea) o el texto menciona un plazo estricto para hoy (reunión hoy, cierre hoy, cliente esperando hoy). Los plazos de días o semanas no son urgencia Alta; Alta es solo para hoy o para bloqueos totales.
   - Si no, ¿es 'Baja'?: si el texto dice que el usuario puede seguir trabajando (tiene alternativa funcional o el problema no le impide trabajar), si es una consulta, o si es un aviso preventivo que no impide trabajar.
   - Si no es ninguna de las anteriores, es 'Media' (dificulta el trabajo, o requiere atención en un plazo de días o semanas pero no para hoy, sin llegar a ser un bloqueo total).
 
5. Invocación obligatoria de la herramienta `calcular_prioridad`:
   - Debes llamar SIEMPRE a la herramienta `calcular_prioridad(impacto=..., urgencia=...)`, excepto únicamente cuando la incidencia no permite saber qué falla y se clasifica como 'requiere más información'.
   - Asegúrate de ejecutar la llamada a la herramienta para obtener la prioridad antes de generar el resumen.
 
6. Proporcionar un resumen breve y estructurado que incluya obligatoriamente una línea con el formato fijo:
   Categoría: <valor>
   (donde <valor> es exactamente Red, Software, Hardware, Accesos o 'requiere más información').
   A continuación incluye el resto de campos:
   - Impacto: (Usuario o Departamento)
   - Urgencia: (Alta, Media o Baja)
   - Prioridad: la prioridad devuelta por la herramienta (ej. P1, P2, P3, P4)
   - Breve justificación de la clasificación asignada.
"""
 
clasificador = LlmAgent(
    name="clasificador",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
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
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
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
# 3. Agente Registrador
# -----------------------------------------------------------------------------
INSTRUCCION_REGISTRADOR = """Eres el agente encargado de registrar la incidencia como ticket en el sistema de soporte de TI.
 
Dispones de la clasificación previa:
{clasificacion}
 
Tu tarea es:
1. Si la clasificación indica 'requiere más información' o no tiene una categoría válida (Red, Software, Hardware o Accesos):
   - NO registres nada y NO llames a ninguna herramienta.
   - Responde exactamente: "Ticket no registrado: la incidencia requiere más información."
2. En cualquier otro caso, llama UNA sola vez a la herramienta `registrar_incidencia` con:
   - descripcion: el texto original de la incidencia tal como lo escribió el usuario;
   - categoria, impacto y urgencia: los valores indicados en la clasificación.
3. Responde en una sola línea con el número de ticket y la prioridad que devuelve la herramienta, con este formato:
   "Ticket <id> registrado con prioridad <prioridad>."
   Si la herramienta devuelve un error, indícalo en una línea.
"""
 
registrador = LlmAgent(
    name="registrador",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    model=model_sencillo_llm,
    instruction=INSTRUCCION_REGISTRADOR,
    tools=[registrar_incidencia],
    output_key="ticket",
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=300,
    ),
)
 
# -----------------------------------------------------------------------------
# 4. Agente Redactor
# -----------------------------------------------------------------------------
INSTRUCCION_REDACTOR = """Eres un asistente de soporte de TI encargado de redactar la respuesta completa de triaje y resolución de incidencias.
 
Dispones de la siguiente información del caso:
- Clasificación y prioridad:
{clasificacion}
 
- Incidencias similares y soluciones:
{similares}
 
- Registro del ticket:
{ticket}
 
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
- Indica al usuario el número de ticket con el que ha quedado registrada su incidencia (aparece en el registro del ticket).
- Explica los pasos a seguir para solventar la incidencia (aprovechando las soluciones de casos similares si aplican) o los siguientes pasos que seguirá el equipo de TI para atender su solicitud.
 
### 2. Nota técnica para el equipo de soporte
- Resumen técnico conciso.
- Detalla el número de ticket, la categoría, el nivel de prioridad asignado (P1-P4), el impacto y la urgencia, junto con los casos similares consultados (IDs y soluciones aplicadas).
"""
 
redactor = LlmAgent(
    name="redactor",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
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
# Pipeline secuencial de triaje
# -----------------------------------------------------------------------------
triaje = SequentialAgent(
    name="triaje",
    description=(
        "Procesa una incidencia nueva de soporte de TI: la clasifica, calcula su "
        "prioridad, busca incidencias similares resueltas, la registra como ticket "
        "y redacta la respuesta."
    ),
    sub_agents=[clasificador, buscador, registrador, redactor],
)
 
# -----------------------------------------------------------------------------
# 5. Agente de Consultas (historial y tickets registrados)
# -----------------------------------------------------------------------------
INSTRUCCION_CONSULTAS = """Eres un asistente que responde preguntas sobre las incidencias de TI del servicio de soporte.
 
Dispones de dos fuentes de datos, cada una con su herramienta:
- `estadisticas_historial`: el historial de incidencias YA RESUELTAS (casos pasados con su solución).
- `consultar_tickets`: los tickets REGISTRADOS por este sistema. Por defecto devuelve los abiertos; usa el parámetro `estado` con 'cerrada' o 'todas' si preguntan por tickets cerrados o por todos.
 
El historial incluye también los tickets que se han cerrado (aparecen con origen 'ticket').
 
Tu tarea es:
1. Elegir la herramienta según la pregunta:
   - Si pregunta por incidencias resueltas, el historial o casos pasados, usa `estadisticas_historial`.
   - Si pregunta por tickets, incidencias abiertas, pendientes, cerradas, registradas o recientes, usa `consultar_tickets`.
   - Si no está claro, usa las dos e indica qué dato corresponde a cada fuente.
2. Si la pregunta se refiere a una categoría (Red, Software, Hardware o Accesos) o a una prioridad (P1, P2, P3 o P4), pásala como filtro en los parámetros de la herramienta.
3. Responder de forma breve y clara usando ÚNICAMENTE los datos que devuelven las herramientas. No inventes cifras ni ejemplos.
4. Si la pregunta no se puede responder con esos datos, dilo claramente e indica qué información sí está disponible.
"""
 
consultas = LlmAgent(
    name="consultas",
    description=(
        "Responde preguntas sobre el historial de incidencias resueltas y sobre los "
        "tickets registrados (incidencias abiertas): cuántas hay, cómo se reparten "
        "por categoría o prioridad, y ejemplos."
    ),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    model=model_sencillo_llm,
    instruction=INSTRUCCION_CONSULTAS,
    tools=[estadisticas_historial, consultar_tickets],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    generate_content_config=genai_types.GenerateContentConfig(
        max_output_tokens=500,
    ),
)
 
# -----------------------------------------------------------------------------
# 6. Agente de Gestión de Tickets (cierre)
# -----------------------------------------------------------------------------
INSTRUCCION_GESTION_TICKETS = """Eres el agente que cierra los tickets de incidencias cuando un técnico indica que están resueltos.
 
Las soluciones de los tickets cerrados se añaden al historial y el sistema las propondrá en futuras incidencias parecidas. Por eso SOLO debes cerrar un ticket si la solución es válida.
 
Sigue estos pasos:
 
1. Identifica en el mensaje el identificador del ticket (formato TCK-0001) y la solución aplicada.
   Si falta alguno de los dos, NO llames a ninguna herramienta: pide en una frase el dato que falta.
 
2. Llama a `ver_ticket` con el identificador para conocer la incidencia original.
   Si devuelve un error (el ticket no existe) o el ticket ya está cerrado, explícalo y no continúes.
 
3. Comprueba la solución. Es VÁLIDA solo si cumple las dos condiciones:
   a) Describe una acción técnica concreta que se realizó (por ejemplo: reinstalar, sustituir, configurar, restablecer, conceder permisos, actualizar, limpiar, reiniciar un servicio o un equipo).
   b) Tiene relación con la incidencia original: actúa sobre el equipo, la aplicación, la red o el acceso afectados, y podría razonablemente resolver ese problema.
   NO es válida si:
   - no tiene relación con la informática o es una broma;
   - es una acción técnica sobre algo distinto de lo que fallaba;
   - es vaga y no dice qué se hizo ("ya funciona", "se arregló", "solucionado").
 
4. Si la solución NO es válida, NO llames a `cerrar_ticket`. Explica en una o dos frases por qué no puedes cerrar el ticket y pide al técnico que indique qué acción concreta resolvió la incidencia.
 
5. Si la solución es válida, llama UNA sola vez a `cerrar_ticket` con el identificador y la solución, redactada de forma clara y breve. Después confirma el cierre e indica que la solución se ha añadido al historial y se usará en futuras incidencias parecidas. Si la herramienta devuelve un error, explícalo.
"""
 
gestion_tickets = LlmAgent(
    name="gestion_tickets",
    description=(
        "Cierra tickets de incidencias resueltas: recibe el identificador del ticket "
        "y la solución aplicada, comprueba que la solución es válida, lo marca como "
        "cerrado y lo añade al historial."
    ),
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    model=model_sencillo_llm,
    instruction=INSTRUCCION_GESTION_TICKETS,
    tools=[ver_ticket, cerrar_ticket],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=300,
    ),
)
 
# -----------------------------------------------------------------------------
# Coordinador (Root Agent)
# -----------------------------------------------------------------------------
INSTRUCCION_COORDINADOR = """Eres el punto de entrada del servicio de soporte de TI. No resuelves nada tú mismo: decides qué agente atiende cada mensaje.
 
Decide según estas reglas, en este orden:
 
1. Si el usuario pide CERRAR o dar por resuelto un ticket ya registrado (normalmente menciona un identificador como TCK-0001 y cómo se solucionó), transfiere a 'gestion_tickets'.
 
2. Si el usuario describe un problema, una avería, un error, una petición o cualquier incidencia nueva (aunque sea muy vaga, como "no funciona"), transfiere a 'triaje'.
 
3. Si el usuario pide datos o estadísticas sobre incidencias YA RESUELTAS del historial, o sobre los TICKETS registrados, abiertos o cerrados (cuántos hay, de qué categoría o prioridad, cómo se reparten, ejemplos), transfiere a 'consultas'.
 
4. En cualquier otro caso, responde tú mismo en una o dos frases, sin transferir. Esto incluye:
   - saludos y despedidas;
   - preguntas sobre ti o sobre el sistema ("¿qué puedes hacer?", "¿cómo funcionas?", "¿quién eres?");
   - mensajes que no son ni una incidencia, ni una pregunta sobre las incidencias, ni un cierre de ticket.
   Explica que puedes registrar y priorizar incidencias nuevas, responder preguntas sobre el historial y los tickets, y cerrar tickets resueltos.
 
Las preguntas sobre lo que puede hacer el sistema NO son preguntas sobre las incidencias: respóndelas tú.
"""
 
root_agent = LlmAgent(
    name="coordinador",
    model=model_sencillo_llm,
    instruction=INSTRUCCION_COORDINADOR,
    sub_agents=[triaje, consultas, gestion_tickets],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=200,
    ),
)
 
app = App(
    root_agent=root_agent,
    name="app",
) 