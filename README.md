# Triaje de incidencias con agentes (ADK + OpenAI)
 
Prototipo de sistema multiagente para un servicio de soporte técnico (TI). Un **coordinador** recibe cada mensaje y lo deriva al agente adecuado:
 
- **Incidencias nuevas** → una cadena de cuatro agentes que la **clasifica**, calcula su **prioridad**, **busca incidencias similares** ya resueltas, la **registra como ticket** y **redacta** una respuesta para el usuario (con su número de ticket) y una nota técnica para el equipo de soporte.
- **Preguntas sobre las incidencias** (el historial de incidencias resueltas o los tickets: cuántas hay, de qué tipo o prioridad, ejemplos) → un agente de **consultas**.
- **Cierre de tickets** (un técnico indica cómo se resolvió) → un agente de **gestión de tickets** que comprueba que la solución es válida, cierra el ticket y lo añade al historial, de modo que el sistema **aprende** de las incidencias que resuelve.
 
Los datos se guardan en una base de datos **SQLite**.
 
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
8. [Escalabilidad](#escalabilidad)
9. [Limitaciones y mejoras](#limitaciones-y-mejoras)
 
---
 
## Arquitectura
 
El sistema combina los **dos patrones de coordinación de ADK**:
 
- **Delegación:** el `coordinador` (un `LlmAgent`) decide, según el mensaje, a qué agente transferirlo: `triaje`, `consultas` o `gestion_tickets`.
- **Cadena:** el `triaje` (un `SequentialAgent`) ejecuta siempre los mismos cuatro pasos en el mismo orden. Cada agente guarda su resultado en el estado de la sesión (`output_key`) y el siguiente lo recibe en sus instrucciones.
 
```
                              Mensaje del usuario
                                      │
                                      ▼
                          ┌───────────────────────┐
                          │      Coordinador      │  decide a quién transferir
                          │     (gpt-5.4-nano)    │  (saludos: responde él mismo)
                          └───────────────────────┘
               incidencia │            │ pregunta          │ cierre de ticket
                          ▼            ▼                   ▼
┌──── triaje (SequentialAgent) ───┐ ┌──────────────┐ ┌──────────────────┐
│ 1. Clasificador                 │ │  Consultas   │ │ Gestión tickets  │
│      calcular_prioridad         │ │              │ │                  │
│ 2. Buscador                     │ │ estadisticas_│ │ ver_ticket       │
│      buscar_incidencias_        │ │ historial    │ │ (comprueba la    │
│      similares                  │ │              │ │  solución)       │
│ 3. Registrador                  │ │ consultar_   │ │ cerrar_ticket    │
│      registrar_incidencia       │ │ tickets      │ │                  │
│ 4. Redactor                     │ └──────────────┘ └──────────────────┘
│      respuesta + nº de ticket   │
└─────────────────────────────────┘
                          │            │                   │
                          ▼            ▼                   ▼
            ┌──────────────────── SQLite (data/soporte.db) ─────────────┐
            │  incidencias_resueltas  ◄── tickets cerrados ──  tickets  │
            └───────────────────────────────────────────────────────────┘
```
 
| Agente | Modelo | Herramienta | Qué hace |
|---|---|---|---|
| Coordinador | `MODELO_SENCILLO` (nano) | — (transferencia de ADK) | Transfiere las incidencias a `triaje`, las preguntas a `consultas` y los cierres de ticket a `gestion_tickets`. Responde él mismo a saludos y preguntas sobre el sistema. |
| Clasificador | `MODELO_SENCILLO` (nano) | `calcular_prioridad` | Determina categoría (Red, Software, Hardware, Accesos), impacto (Usuario / Departamento) y urgencia (Alta / Media / Baja). Si la incidencia es demasiado vaga, indica que requiere más información. |
| Buscador | `MODELO_SENCILLO` (nano) | `buscar_incidencias_similares` | Busca en el historial las incidencias resueltas más parecidas dentro de la misma categoría. |
| Registrador | `MODELO_SENCILLO` (nano) | `registrar_incidencia` | Registra la incidencia como ticket abierto (`TCK-0001`, `TCK-0002`…). La prioridad la calcula la herramienta, no el modelo. Si la incidencia requiere más información, no registra nada. |
| Redactor | `MODELO_REDACCION` (mini) | — | Redacta la respuesta al usuario (con su número de ticket) y la nota técnica. Si falta información, pide al usuario los datos concretos. |
| Consultas | `MODELO_SENCILLO` (nano) | `estadisticas_historial`, `consultar_tickets` | Responde preguntas sobre el historial de incidencias resueltas y sobre los tickets abiertos o cerrados (totales, reparto por categoría o prioridad, ejemplos), usando solo los datos de las herramientas. |
| Gestión de tickets | `MODELO_SENCILLO` (nano) | `ver_ticket`, `cerrar_ticket` | Lee el ticket, comprueba que la solución es una acción técnica concreta relacionada con la incidencia y, solo entonces, lo cierra y lo añade al historial. |
 
Los agentes especialistas tienen desactivada la transferencia a otros agentes (`disallow_transfer_to_parent` y `disallow_transfer_to_peers`), de modo que cada uno solo hace su tarea.
 
### Datos (SQLite)
 
Los datos se guardan en `data/soporte.db`, una base de datos SQLite que se crea sola la primera vez (Python incluye SQLite, no hay que instalar nada):
 
| Tabla | Contenido |
|---|---|
| `incidencias_resueltas` | Historial de incidencias resueltas con su solución. Al crearse se cargan las 40 de `data/incidencias_resueltas.csv` (origen `historial`); después se añaden los tickets que se cierran (origen `ticket`) |
| `tickets` | Tickets registrados por el sistema: estado `abierta` o `cerrada`, fecha de cierre y solución |
 
Cerrar un ticket actualiza su estado y lo copia al historial **en la misma transacción**: o se hacen las dos operaciones o ninguna.
 
### El ciclo de aprendizaje
 
```
Incidencia nueva → ticket abierto → un técnico lo cierra con la solución
       ▲                                        │
       │                                        ▼
       └── el buscador propone esa solución ◄── pasa al historial
           en incidencias parecidas
```
 
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
│   ├── agent.py              # Coordinador, cadena de triaje (4 agentes), consultas y gestión de tickets
│   ├── tools.py              # Function tools: calcular_prioridad y buscar_incidencias_similares
│   ├── tools_consultas.py    # Function tool: estadisticas_historial
│   ├── tickets.py            # Function tools: registrar_incidencia, consultar_tickets, ver_ticket y cerrar_ticket
│   ├── db.py                 # Base de datos SQLite: creación de tablas y carga del historial inicial
│   └── finops.py             # Callbacks de medición de coste y límites de gasto
├── data/
│   ├── incidencias_resueltas.csv   # Datos iniciales del historial (40 incidencias resueltas)
│   └── soporte.db                  # Base de datos SQLite (generada, excluida de git)
├── scripts/
│   ├── probar_key.py         # Verifica la API key y lista los modelos disponibles (SDK de OpenAI)
│   ├── informe_costes.py     # Informe FinOps a partir de logs/costes.csv
│   ├── evaluar.py            # Evaluación automática del clasificador
│   ├── evaluar_coordinador.py  # Evaluación del enrutado del coordinador
│   └── evaluar_cierres.py    # Evaluación de la validación de soluciones al cerrar tickets
├── tests/
│   ├── unit/                 # Tests unitarios (no llaman a OpenAI; cada uno con su base de datos temporal)
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
 
Abrir http://127.0.0.1:8000, seleccionar el agente `app` y escribir un mensaje. Usar una **sesión nueva para cada mensaje**.
 
Ejemplo:
 
> Desde esta mañana no puedo conectarme a la VPN, me da error de certificado, y tengo una reunión con un cliente a las 12
 
Resultado esperado: el coordinador lo transfiere a `triaje`; categoría Red, impacto Usuario, urgencia Alta, prioridad P2; se registra un ticket (por ejemplo, `TCK-0001`) y la respuesta incluye ese número y una solución basada en la incidencia INC-001 del historial.
 
Otros ejemplos:
- *¿Cuántas incidencias de Red hay en el historial?* → lo responde el agente de consultas (10).
- *¿Cuántos tickets hay abiertos?* → lo responde el agente de consultas con los tickets registrados.
- *No funciona* → se pide más información y no se registra ningún ticket.
- *Cierra el TCK-0001, se reinstaló el certificado de la VPN* → el agente de gestión comprueba la solución, cierra el ticket y lo añade al historial.
- *Cierra el TCK-0002, se arregló comiendo una pizza* → el ticket no se cierra y se pide la solución real.
- *Hola, ¿qué puedes hacer?* → responde el coordinador.
 
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
| `MODELO_SENCILLO` | Sí | Modelo de todos los agentes salvo el redactor (p. ej. `openai/gpt-5.4-nano-2026-03-17`) |
| `MODELO_REDACCION` | Sí | Modelo del redactor (p. ej. `openai/gpt-5.4-mini-2026-03-17`) |
| `MAX_TOKENS_INCIDENCIA` | No | Límite de tokens por incidencia (por defecto 20000) |
| `PRESUPUESTO_TOTAL_USD` | No | Presupuesto total del proyecto en USD (por defecto 5) |
| `RUTA_BD` | No | Ruta de la base de datos SQLite (por defecto `data/soporte.db`). Los tests y las evaluaciones usan bases de datos aparte |
 
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
 
El informe muestra el gasto acumulado frente al presupuesto, el coste medio por incidencia, cuánto aporta cada agente al coste de una incidencia, el desglose global por agente y una proyección a 1.000 incidencias al mes.
 
Para el coste por incidencia solo cuenta las **incidencias completas** (sesiones que llegan al redactor). Las evaluaciones, las consultas sobre el historial y los saludos se muestran aparte: cuentan en el gasto total y en el presupuesto, pero no distorsionan el coste por incidencia.
 
### Límites
 
| Mecanismo | Dónde | Qué hace |
|---|---|---|
| Tokens de salida máximos | `generate_content_config` de cada agente | Evita respuestas innecesariamente largas |
| Presupuesto por incidencia | `before_model_callback` + `MAX_TOKENS_INCIDENCIA` | Si una sesión supera el límite, no se llama al modelo |
| Presupuesto total | `before_model_callback` + `PRESUPUESTO_TOTAL_USD` | Si se alcanza el presupuesto, no se llama al modelo |
 
### Optimizaciones aplicadas
 
- Modelo **nano** para las tareas sencillas (enrutar, clasificar, buscar, registrar, consultar y gestionar cierres); **mini** solo para redactar.
- La prioridad, la búsqueda, el registro, el cierre y las estadísticas se calculan en **Python**, sin gastar tokens.
- **Temperatura 0** en el coordinador, el clasificador, el registrador y el agente de gestión de tickets, para decisiones consistentes.
- Los callbacks de FinOps se aplican a **todos** los agentes, incluidos los añadidos después: un agente nuevo queda medido y limitado desde el primer momento.
 
### Resultados
 
Coste de una **incidencia completa** (coordinador + cadena de triaje), por agente:
 
| Agente | Llamadas por incidencia | Coste aprox. (USD) |
|---|---|---|
| Coordinador | 1 | 0,00016 |
| Clasificador | 2 | 0,0007 |
| Buscador | 2 | 0,0008 |
| Registrador | 2 | 0,0002 |
| Redactor | 1 | 0,0025 |
| **Total** | | **≈ 0,0044** |
 
| Métrica | Valor |
|---|---|
| Coste por incidencia completa | ≈ 0,0044 USD |
| Proyección a 1.000 incidencias/mes | ≈ 4,4 USD |
| Agente más caro | Redactor (~58 % del coste de una incidencia) |
| Sobrecoste del coordinador | ≈ 3 % por incidencia |
| Coste de una evaluación completa del clasificador (28 casos) | ≈ 0,02 USD |
 
Precios usados (USD por millón de tokens): gpt-5.4-nano 0,20 entrada / 1,25 salida; gpt-5.4-mini 0,75 entrada / 4,50 salida.
 
---
 
## Tests y evaluación
 
### Tests unitarios
 
```bash
uv run pytest tests/unit
```
 
Comprueban, **sin llamar a OpenAI**:
- la estructura del sistema (coordinador, cadena de triaje con sus cuatro agentes en orden, agentes de consultas y de gestión de tickets, modelos, herramientas, `output_key` y transferencias desactivadas en los especialistas);
- las herramientas (los seis casos de la matriz de prioridad, valores inválidos, la búsqueda, las estadísticas del historial, y el registro, la consulta, la lectura y el cierre de tickets);
- la base de datos (creación de tablas, carga del historial sin duplicados, deshacer cambios ante un error) y el ciclo de aprendizaje (un ticket cerrado aparece en las búsquedas);
- que cada test usa su propia base de datos temporal (`tests/unit/conftest.py`), sin tocar la real;
- el control de costes (cálculo, registro, corte por presupuesto y separación de incidencias completas en el informe);
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
 
| Métrica | Evaluación inicial (18 casos) | Tras el ajuste (28 casos) | Tras añadir el coordinador (28 casos) |
|---|---|---|---|
| Categoría | 94 % | 92 % | 96 % |
| Impacto | 71 % | 96 % | 96 % |
| Urgencia | 65 % | 85 % | 88 % |
| Prioridad | 59 % | 85 % | 88 % |
| Casos totalmente correctos | 61 % | 79 % | 86 % |
| **Validación** | — | **70 %** | **90 %** |
 
La última columna no corresponde a ningún cambio en las reglas del clasificador: al integrarlo bajo el coordinador cambia ligeramente el contexto que recibe el modelo. Con solo 10 casos de validación, cada caso vale 10 puntos, por lo que el acierto en validación debe leerse como un rango (**70–90 %**) y no como una cifra exacta.
 
**Análisis de los fallos restantes:**
- El modelo tiende a sobrestimar la urgencia: le cuesta asignar **Baja** aunque el texto indique que el usuario puede seguir trabajando.
- Algunas reglas basadas en palabras concretas ("entrar", "equipo") tienen **efectos secundarios** en casos que no se habían previsto.
- Un ajuste produjo una **regresión** (el caso de la contraseña dejó de clasificarse como Accesos), detectada gracias a la evaluación.
 
### Evaluación del enrutado del coordinador
 
```bash
uv run python scripts/evaluar_coordinador.py
```
 
Envía 11 mensajes (5 incidencias, 3 preguntas sobre el historial, 1 sobre los tickets, 1 cierre de ticket y 1 saludo) y comprueba a qué agente los transfiere el coordinador. Usa su propia base de datos (`logs/soporte_evaluacion.db`), separada de la real.
 
| Resultado | Valor |
|---|---|
| Enrutado correcto (versión con 9 mensajes) | **9/9 (100 %)** |
| Enrutado correcto (versión con 10 mensajes) | **10/10 (100 %)** |
| Enrutado correcto (versión actual, 11 mensajes) | **11/11 (100%)** |
 
En una primera versión, el coordinador enviaba el saludo "¿qué puedes hacer?" al agente de consultas. Se corrigió ordenando sus reglas y aclarando que las preguntas sobre el propio sistema no son preguntas sobre el historial.
 
### Evaluación del cierre de tickets
 
```bash
uv run python scripts/evaluar_cierres.py
```
 
Registra 8 tickets en una base de datos de evaluación (que se vacía en cada ejecución) e intenta cerrarlos con 4 soluciones válidas y 4 no válidas: 2 absurdas, 1 técnica pero sin relación con la incidencia y 1 vaga. Comprueba en la base de datos si cada ticket quedó cerrado o abierto.
 
| Resultado | Valor |
|---|---|
| Decisiones correctas | **8/8 (100 %)** |
| Cierres con solución no válida (falsos cierres) | **0** |
| Soluciones válidas rechazadas (falsos rechazos) | **0** |
 
Los falsos cierres son el error más grave, porque introducirían soluciones incorrectas en el historial, que el sistema propondría después en incidencias parecidas.
 
---
 
## Decisiones de diseño
 
- **Varios agentes en lugar de uno:** cada uno tiene una responsabilidad clara, su propio modelo y su propia medición de coste. Si algo falla, se sabe en qué paso.
- **Cadena para el triaje (`SequentialAgent`):** el proceso de una incidencia sigue siempre los mismos pasos en el mismo orden, así que no hace falta que un modelo decida el orden.
- **Delegación para la entrada (coordinador):** el tipo de mensaje varía (incidencia, consulta, saludo), así que aquí sí hace falta un agente que decida a quién transferirlo.
- **Extensibilidad:** el agente de consultas, el registrador y el agente de gestión de tickets se añadieron sin modificar el clasificador ni el buscador: cada uno es un `LlmAgent` nuevo con su herramienta, colgado del coordinador o insertado en la cadena. Cada ampliación se desarrolló en una rama de git aparte y se unió a la principal tras pasar los tests y la evaluación del enrutado.
- **Acciones, no solo respuestas:** el registrador guarda cada incidencia como ticket y el agente de gestión los cierra, de modo que el sistema actúa y acumula datos que luego se pueden consultar. La prioridad del ticket la calcula la herramienta (reutilizando `calcular_prioridad`), no el modelo, para que sea siempre coherente.
- **Un sistema que aprende, protegido frente a datos malos:** los tickets cerrados pasan al historial y el buscador los usa. Como una solución incorrecta contaminaría el historial, el agente de gestión lee la incidencia original y solo cierra si la solución es una acción técnica concreta relacionada con ella. Esta validación se evalúa con casos válidos y no válidos.
- **SQLite:** una base de datos real (tablas, consultas SQL, transacciones) sin instalar ningún servidor. Se crea sola y carga los datos iniciales del CSV. Cerrar un ticket y copiarlo al historial se hace en una única transacción.
- **Function tools deterministas:** la prioridad, la búsqueda y el registro deben dar siempre el mismo resultado, así que se implementan en Python. Son testeables y no consumen tokens; el modelo solo decide cuándo usarlas y con qué datos.
- **ADK + LiteLLM:** ADK permite usar cualquier proveedor. El modelo se elige por configuración, por lo que cambiar de proveedor no requiere cambiar el código, solo volver a pasar la evaluación.
- **SDK frente a ADK:** el script `probar_key.py` usa directamente el SDK de OpenAI porque es una llamada única; el sistema de triaje usa ADK porque necesita agentes, herramientas y coordinación.
- **Desarrollo asistido con Antigravity:** el código se desarrolló con el agente de Antigravity, controlado mediante las reglas de `AGENTS.md` (sin acceso a secretos, tests obligatorios y aprobación previa de los cambios).
 
---
 
## Escalabilidad
 
### Coste: crece de forma lineal y está controlado
 
El coste depende solo del número de incidencias, y cada una cuesta lo mismo (≈ 0,0044 USD):
 
| Volumen mensual | Coste estimado |
|---|---|
| 1.000 incidencias | ≈ 4,4 USD |
| 10.000 incidencias | ≈ 44 USD |
| 100.000 incidencias | ≈ 440 USD |
 
Lo que permite que escale de forma eficiente:
- Los modelos baratos (nano) hacen la mayor parte del trabajo; el modelo más caro (mini) solo se usa en un paso.
- Todo lo que es determinista (prioridad, búsqueda, registro, cierre, estadísticas) se hace en Python y no consume tokens.
- Cada llamada al modelo queda medida, y los límites por incidencia y el presupuesto total evitan que un error o un abuso dispare el gasto.
- El informe de costes indica qué agente concentra el gasto, que es donde optimizar primero (actualmente, el redactor).
 
### Arquitectura: preparada para varias instancias
 
- Los agentes no guardan estado propio: el estado de cada incidencia vive en la sesión de ADK. Por eso se pueden ejecutar varias copias del sistema en paralelo.
- La plantilla Agent Starter Pack ya incluye el despliegue en **Cloud Run** (que escala automáticamente según la carga) o en **Agent Engine**.
- Para varias instancias habría que pasar las sesiones de memoria a un almacenamiento persistente compartido (la plantilla permite Cloud SQL o las sesiones de Agent Engine).
 
### Datos: lo que habría que cambiar a gran escala
 
| Componente | Prototipo | A gran escala |
|---|---|---|
| Historial y tickets | SQLite local (un único fichero) | Servidor de base de datos compartido (por ejemplo, PostgreSQL en Cloud SQL) o la propia herramienta de tickets, para que varias instancias escriban a la vez |
| Búsqueda de similares | Palabras en común, recorriendo el historial de la categoría | Índice o búsqueda semántica con vectores |
| Registro de costes | CSV local | Base de datos o BigQuery, con un panel de control |
 
Como cada fuente de datos está aislada en una function tool, estos cambios no afectan a los agentes: solo cambia el código de la herramienta.
 
### Funciones: el sistema crece sin rehacer lo que hay
 
- Los agentes de consultas, registro y gestión de tickets se añadieron sin modificar el clasificador ni el buscador.
- Cualquier agente nuevo hereda automáticamente los callbacks de FinOps (medición y límites).
- Las evaluaciones son baratas y automáticas, por lo que se pueden repetir tras cada cambio para comprobar que nada se estropea.
 
---
 
## Limitaciones y mejoras
 
- **Urgencia Baja:** mejorar su detección y medir la mejora con un conjunto de validación nuevo y más grande, para obtener una cifra de acierto más estable.
- **Permisos para cerrar tickets:** ahora cualquiera que use el chat puede cerrar un ticket. En un sistema real solo podrían hacerlo los técnicos identificados, y quedaría registrado quién cerró cada uno.
- **Revisión humana del historial:** la validación del agente frena las soluciones absurdas, pero no es infalible. Las soluciones de tickets cerrados podrían entrar como pendientes de validar y usarse solo tras la aprobación de un supervisor.
- **Sistema de tickets real:** sustituir la base de datos SQLite por la herramienta de tickets de la empresa. Al estar aislada en function tools, el cambio no afecta a los agentes.
- **Búsqueda semántica:** la búsqueda actual compara palabras; podría mejorarse para encontrar casos parecidos por significado.
- **Despliegue:** Cloud Run o Agent Engine, con la key en Secret Manager y CI/CD (la plantilla Agent Starter Pack permite añadirlo con `agent-starter-pack enhance`).
- **Optimización de costes:** evaluar si el redactor puede usar nano manteniendo la calidad, lo que reduciría el coste total aproximadamente a la mitad.
- **Incidencias masivas:** los tickets abiertos solo se consultan, el buscador los podría usar para detectar si varias personas reportan lo mismo en poco tiempo y si es así, subir el impacto a Departamento.
 