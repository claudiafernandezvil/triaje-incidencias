# Reglas del proyecto de triaje de incidencias
 
## Seguridad (obligatorio)

- NUNCA leas, muestres ni modifiques el fichero .env.

- NUNCA escribas API keys ni secretos en el código, en tests ni en la documentación.

- La configuración se lee siempre de variables de entorno.

- Si necesitas una variable nueva, añádela vacía a .env.example y avísame.
 
## Calidad

- Código Python siguiendo PEP 8.

- Toda función nueva en app/tools.py debe tener su test en tests/.

- Ejecuta los tests después de cada cambio y muéstrame el resultado.
 
## Forma de trabajar

- Antes de cambios grandes, explícame el plan y espera mi aprobación.

- Pídeme permiso antes de ejecutar comandos en la terminal.

- Respeta la estructura generada por la plantilla Agent Starter Pack.

- El modelo LLM se usa con OpenAI a través de LiteLLM; no uses Vertex AI ni Google Cloud.

- Los modelos se leen de las variables MODELO_SENCILLO y MODELO_REDACCION.
 