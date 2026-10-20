# Triaje de incidencias con agentes (ADK + OpenAI)
 
Prototipo de sistema multiagente que recibe una incidencia de soporte técnico (TI), la **clasifica**, calcula su **prioridad**, **busca incidencias similares** ya resueltas y **redacta** una respuesta para el usuario y una nota técnica para el equipo de soporte.
 
Desarrollado con **Google Agent Development Kit (ADK)**, modelos de **OpenAI** a través de **LiteLLM**, y generado a partir de la plantilla **Agent Starter Pack** (cookiecutter).
 
---
 
## Índice
 
1. [Arquitectura](#arquitectura)
2. [Estructura del proyecto](#estructura-del-proyecto)
3. [Instalación y ejecución](#instalación-y-ejecución)
4. [Gestión de la API key](#gestión-de-la-api-key)
5. [FinOps: control de costes](#finops-control-de-costes)
6. [Tests y evaluación](#tests-y-evaluación)
7. [Decisiones de diseño](#decisiones-de-diseño)
8. [Limitaciones y siguientes pasos](#limitaciones-y-siguientes-pasos)
 
---
 
## Arquitectura
 
Tres agentes `LlmAgent` coordinados en cadena por un `SequentialAgent`. Cada agente guarda su resultado en el estado de la sesión (`output_key`) y el siguiente lo recibe en sus instrucciones.
 
```
Incidencia del usuario
        │
        ▼
┌───────────────────┐   calcular_prioridad (matriz impacto × urgencia)
│ 1. Clasificador   │──────────────────────────────────────────────►  P1–P4
│    (gpt-5.4-nano) │   output_key = "clasificacion"
└───────────────────┘
        │
        ▼
┌───────────────────┐   buscar_incidencias_similares (historial CSV)
│ 2. Buscador       │──────────────────────────────────────────────►  casos similares
│    (gpt-5.4-nano) │   output_key = "similares"
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 3. Redactor       │──►  Respuesta para el usuario + nota técnica
│    (gpt-5.4-mini) │
└───────────────────┘
```
 
| Agente | Modelo | Herramienta | Qué hace |
|---|---|---|---|
| Clasificador | `MODELO_SENCILLO` (nano) | `calcular_prioridad` | Determina categoría (Red, Software, Hardware, Accesos), impacto (Usuario / Departamento) y urgencia (Alta / Media / Baja). Si la incidencia es demasiado vaga, indica que requiere más información. |
| Buscador | `MODELO_SENCILLO` (nano) | `buscar_incidencias_similares` | Busca en el historial las incidencias resueltas más parecidas dentro de la misma categoría. |
| Redactor | `MODELO_REDACCION` (mini) | — | Redacta la respuesta al usuario y la nota técnica. Si falta información, pide al usuario los datos concretos. |
 
**Matriz de prioridad** (implementada en Python, determinista):
 
| Impacto \ Urgencia | Alta | Media | Baja |
|---|---|---|---|
| **Departamento** | P1 | P2 | P3 |
| **Usuario** | P2 | P3 | P4 |
 
---
 
## Estructura del proyecto
 
```
triaje-incidencias/
├── app/
│   ├── agent.py              # Definición de los tres agentes y del SequentialAgent
│   ├── tools.py              # Function tools: calcular_prioridad y buscar_incidencias_similares
│   └── finops.py             # Callbacks de medición de coste y límites de gasto
├── data/
│   └── incidencias_resueltas.csv   # Historial de 40 incidencias resueltas
├── scripts/
│   ├── probar_key.py         # Verifica la API key y lista los modelos disponibles (SDK de OpenAI)
│   ├── informe_costes.py     # Informe FinOps a partir de logs/costes.csv
│   └── evaluar.py            # Evaluación automática del clasificador
├── tests/
│   ├── unit/                 # Tests unitarios (no llaman a OpenAI)
│   └── eval/
│       ├── casos_evaluacion.json   # 28 casos con resultado esperado
│       ├── resultado_inicial.md    # Primera evaluación
│       ├── resultado_ajustado.md   # Evaluación tras el ajuste
│       └── ultimo_resultado.md     # Última ejecución
├── AGENTS.md                 # Reglas para el agente de desarrollo (Antigravity)
├── .env.example              # Variables de entorno necesarias (sin valores)
└── pyproject.toml            # Dependencias (gestionadas con uv)
```
 
---
 
## Instalación y ejecución
 
### Requisitos
 
- Python 3.11 o superior
- [uv](https://docs.astral.sh/uv/)
- Una API key de OpenAI
 
### Pasos
 
```bash
# 1. Instalar dependencias
uv sync
 
# 2. Configurar variables de entorno
cp .env.example .env
#    y rellenar los valores en .env (ver sección siguiente)
 
# 3. (Opcional) Comprobar que la key funciona
uv run python scripts/probar_key.py
 
# 4. Arrancar la interfaz web de ADK
uv run adk web
```
 
Abrir http://127.0.0.1:8000, seleccionar el agente `app` y escribir una incidencia. Usar una **sesión nueva para cada incidencia**.
 
Ejemplo:
 
> Desde esta mañana no puedo conectarme a la VPN, me da error de certificado, y tengo una reunión con un cliente a las 12
 
Resultado esperado: categoría Red, impacto Usuario, urgencia Alta, prioridad P2, y una solución basada en la incidencia INC-001 del historial.
 
---
 
## Gestión de la API key
 
La API key **nunca se escribe en el código ni se sube al repositorio**.
 
| Fichero | Contiene la key | Se sube a git |
|---|---|---|
| `.env` | Sí | No (incluido en `.gitignore`) |
| `.env.example` | No, solo los nombres de las variables | Sí |
 
- El código lee la configuración de **variables de entorno**. La librería LiteLLM toma `OPENAI_API_KEY` directamente del entorno; el código solo comprueba que existe.
- Si falta una variable obligatoria, la aplicación **falla al arrancar con un mensaje claro**.
- La key no se imprime ni se registra en ningún log.
- El agente de desarrollo (Antigravity) tiene prohibido leer o modificar `.env` mediante las reglas de `AGENTS.md`.
 
### Variables de entorno
 
| Variable | Obligatoria | Descripción |
|---|---|---|
| `OPENAI_API_KEY` | Sí | API key de OpenAI |
| `MODELO_SENCILLO` | Sí | Modelo del clasificador y el buscador (p. ej. `openai/gpt-5.4-nano-2026-03-17`) |
| `MODELO_REDACCION` | Sí | Modelo del redactor (p. ej. `openai/gpt-5.4-mini-2026-03-17`) |
| `MAX_TOKENS_INCIDENCIA` | No | Límite de tokens por incidencia (por defecto 20000) |
| `PRESUPUESTO_TOTAL_USD` | No | Presupuesto total del proyecto en USD (por defecto 5) |
 
Se usan versiones de modelo **con fecha fija** para que los resultados de la evaluación sean reproducibles.
 
### En producción
 
En un despliegue (por ejemplo, Cloud Run o Agent Engine) no existe fichero `.env`: la key se guardaría en **Google Cloud Secret Manager** y se inyectaría como variable de entorno al arrancar. El código funciona igual sin cambios.
 
### Si la key se filtra
 
1. Revocarla inmediatamente en la consola de OpenAI.
2. Crear una nueva.
3. Sustituirla en `.env` (o en Secret Manager).
 
---
 
## FinOps: control de costes
 
### Medición
 
Un `after_model_callback` de ADK registra cada llamada al modelo en `logs/costes.csv` (excluido de git): fecha, sesión, agente, modelo, tokens de entrada y salida, y coste en USD.
 
```bash
uv run python scripts/informe_costes.py
```
 
El informe muestra el gasto acumulado frente al presupuesto, el coste medio por incidencia, el desglose por agente y una proyección a 1.000 incidencias al mes.
 
### Límites
 
| Mecanismo | Dónde | Qué hace |
|---|---|---|
| Tokens de salida máximos | `generate_content_config` de cada agente | Evita respuestas innecesariamente largas |
| Presupuesto por incidencia | `before_model_callback` + `MAX_TOKENS_INCIDENCIA` | Si una sesión supera el límite, no se llama al modelo |
| Presupuesto total | `before_model_callback` + `PRESUPUESTO_TOTAL_USD` | Si se alcanza el presupuesto, no se llama al modelo |
 
### Optimizaciones aplicadas
 
- Modelo **nano** para las tareas sencillas (clasificar y buscar); **mini** solo para redactar.
- La prioridad y la búsqueda se calculan en **Python**, sin gastar tokens.
- **Temperatura 0** en el clasificador, para resultados consistentes.
 
### Resultados
 
| Métrica | Valor |
|---|---|
| Coste medio por incidencia | ~0,005 USD |
| Proyección a 1.000 incidencias/mes | ~5 USD |
| Agente más caro | Redactor (~70 % del gasto) |
| Coste de una evaluación completa (28 casos) | ~0,02 USD |
 
Precios usados (USD por millón de tokens): gpt-5.4-nano 0,20 entrada / 1,25 salida; gpt-5.4-mini 0,75 entrada / 4,50 salida.
 
---
 
## Tests y evaluación
 
### Tests unitarios
 
```bash
uv run pytest tests/unit
```
 
Comprueban, **sin llamar a OpenAI**:
- la estructura del sistema (tres agentes en orden, modelos, herramientas y `output_key`);
- las herramientas (los seis casos de la matriz de prioridad, valores inválidos y la búsqueda);
- el control de costes (cálculo, registro y corte por presupuesto);
- que la aplicación falla si faltan variables de entorno.
 
### Evaluación del clasificador
 
```bash
uv run python scripts/evaluar.py
```
 
Ejecuta el clasificador sobre los 28 casos de `tests/eval/casos_evaluacion.json` y compara categoría, impacto, urgencia y prioridad con el resultado esperado. Los casos se dividen en tres conjuntos:
 
| Conjunto | Casos | Uso |
|---|---|---|
| `ajuste` | 13 | Usados para ajustar las instrucciones |
| `nuevo` | 5 | No vistos en el primer ajuste; sus fallos se usaron en el segundo |
| `validacion` | 10 | **Nunca** usados para ajustar; se ejecutan solo al final |
 
### Resultados
 
| Métrica | Evaluación inicial (18 casos) | Tras el ajuste (28 casos) |
|---|---|---|
| Categoría | 94 % | 92 % |
| Impacto | 71 % | 96 % |
| Urgencia | 65 % | 85 % |
| Prioridad | 59 % | 85 % |
| Casos totalmente correctos | 61 % | 79 % |
| **Validación** | — | **70 %** |
 
**Análisis de los fallos restantes:**
- El modelo tiende a sobrestimar la urgencia: le cuesta asignar **Baja** aunque el texto indique que el usuario puede seguir trabajando.
- Algunas reglas basadas en palabras concretas ("entrar", "equipo") tienen **efectos secundarios** en casos que no se habían previsto.
- Un ajuste produjo una **regresión** (el caso de la contraseña dejó de clasificarse como Accesos), detectada gracias a la evaluación.
 
---
 
## Decisiones de diseño
 
- **Tres agentes en lugar de uno:** cada uno tiene una responsabilidad clara, su propio modelo y su propia medición de coste. Si algo falla, se sabe en qué paso.
- **`SequentialAgent`:** el proceso sigue siempre los mismos pasos en el mismo orden, por lo que no hace falta un coordinador que decida.
- **Function tools deterministas:** la prioridad y la búsqueda deben dar siempre el mismo resultado, así que se implementan en Python. Son testeables y no consumen tokens; el modelo solo decide cuándo usarlas y con qué datos.
- **ADK + LiteLLM:** ADK permite usar cualquier proveedor. El modelo se elige por configuración, por lo que cambiar de proveedor no requiere cambiar el código, solo volver a pasar la evaluación.
- **SDK frente a ADK:** el script `probar_key.py` usa directamente el SDK de OpenAI porque es una llamada única; el sistema de triaje usa ADK porque necesita agentes, herramientas y coordinación.
- **Desarrollo asistido con Antigravity:** el código se desarrolló con el agente de Antigravity, controlado mediante las reglas de `AGENTS.md` (sin acceso a secretos, tests obligatorios y aprobación previa de los cambios).
 
---
 
## Limitaciones y siguientes pasos
 
- **Urgencia Baja:** mejorar su detección y medir la mejora con un conjunto de validación nuevo.
- **Historial real:** conectar `buscar_incidencias_similares` a la base de datos de la herramienta de tickets en lugar del CSV. La búsqueda actual compara palabras; podría mejorarse con búsqueda semántica.
- **Despliegue:** Cloud Run o Agent Engine, con la key en Secret Manager y CI/CD (la plantilla Agent Starter Pack permite añadirlo con `agent-starter-pack enhance`).
- **Optimización de costes:** evaluar si el redactor puede usar nano manteniendo la calidad, lo que reduciría el coste total aproximadamente a la mitad.