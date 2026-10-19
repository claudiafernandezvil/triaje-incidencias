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
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models.lite_llm import LiteLlm

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

# Asegurar formato de LiteLLM para proveedores (ej. 'openai/<modelo>')
model_identifier = (
    modelo_sencillo
    if "/" in modelo_sencillo
    else f"openai/{modelo_sencillo}"
)

INSTRUCTION = """Eres un asistente especializado en el triaje y clasificación inicial de incidencias técnicas en el departamento de TI.

Tu única tarea es analizar la descripción de la incidencia técnica proporcionada y clasificarla de forma precisa exactamente en una de las siguientes cuatro categorías:
1. Red: incidencias relacionadas con conectividad, red local, Wi-Fi, VPN, switches, routers, DNS o acceso a internet.
2. Software: incidencias de aplicaciones, correo electrónico, ofimática, programas informáticos, fallos del sistema operativo o errores de software.
3. Hardware: fallos físicos en ordenadores, portátiles, monitores, teclados, ratones, impresoras, cables o cualquier componente físico averiado.
4. Accesos: gestión de permisos, desbloqueo de usuarios, restablecimiento o expiración de contraseñas, roles de acceso y altas o bajas de cuentas.

Reglas:
- Identifica claramente la categoría asignada (Red, Software, Hardware o Accesos).
- Aporta una justificación breve y concisa de la clasificación asignada.
- Si la información es insuficiente o ambigua, solicita al usuario los detalles necesarios para poder clasificar la incidencia."""

root_agent = Agent(
    name="root_agent",
    model=LiteLlm(model=model_identifier),
    instruction=INSTRUCTION,
)

app = App(
    root_agent=root_agent,
    name="app",
)
