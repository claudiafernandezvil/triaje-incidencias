# Último Resultado de Evaluación del Clasificador

- **Fecha (UTC):** 2026-10-20 06:55:34
- **Modelo evaluado:** `openai/gpt-5.4-nano-2026-03-17`
- **Total de casos evaluados:** 28

## 1. Resumen de Aciertos

| Métrica | Aciertos | Porcentaje |
| :--- | :---: | :---: |
| **Casos totalmente correctos (Global)** | 22/28 | 78.6% |
| Conjunto `ajuste` | 12/13 | 92.3% |
| Conjunto `nuevo` | 3/5 | 60.0% |
| Conjunto `validacion` | 7/10 | 70.0% |

### Precisión por Campo (Casos Estándar)

| Campo | Aciertos | Porcentaje |
| :--- | :---: | :---: |
| Categoría | 24/26 | 92.3% |
| Impacto | 25/26 | 96.2% |
| Urgencia | 22/26 | 84.6% |
| Prioridad | 22/26 | 84.6% |

## 2. Consumo y Costes FinOps

| Concepto | Cantidad |
| :--- | :---: |
| Tokens de entrada (prompt) | 80,924 |
| Tokens de salida (completion) | 2,837 |
| Tokens totales | 83,761 |
| Coste total estimado | **$0.019731 USD** |

## 3. Tabla de Fallos

| ID | Conjunto | Incidencia | Discrepancias (Esperado vs Obtenido) |
| :---: | :---: | :--- | :--- |
| EV-03 | `ajuste` | Me salta un aviso de que mi contraseña caduca en 3... | Categoría: esperado='Accesos', obtenido='Software' |
| EV-16 | `nuevo` | El ventilador del portátil hace un ruido raro, per... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P4', obtenido='P3' |
| EV-17 | `nuevo` | A una compañera nueva le falta acceso a la carpeta... | Impacto: esperado='Usuario', obtenido='Departamento'<br>Urgencia: esperado='Media', obtenido='Alta'<br>Prioridad: esperado='P3', obtenido='P1' |
| EV-19 | `validacion` | El lector de tarjetas de la entrada no funciona y ... | Categoría: esperado='Hardware', obtenido='Accesos' |
| EV-23 | `validacion` | Una tecla del teclado del portátil se queda pegada... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P4', obtenido='P3' |
| EV-25 | `validacion` | La red por cable de toda la tercera planta va algo... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P3', obtenido='P2' |

## 4. Detalle de Ejecución por Caso

| ID | Conjunto | Categoría (Esp / Obt) | Impacto (Esp / Obt) | Urgencia (Esp / Obt) | Prioridad (Esp / Obt) | Estado | Tokens | Coste ($) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| EV-01 | `ajuste` | Red / Red | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3119 | $0.000730 |
| EV-02 | `ajuste` | Hardware / Hardware | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3096 | $0.000716 |
| EV-03 | `ajuste` | Accesos / Software | Usuario / Usuario | Baja / Baja | P4 / P4 | ❌ Fallo | 3097 | $0.000715 |
| EV-04 | `ajuste` | Software / Software | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3110 | $0.000727 |
| EV-05 | `ajuste` | Hardware / Hardware | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3115 | $0.000740 |
| EV-06 | `ajuste` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3090 | $0.000717 |
| EV-07 | `ajuste` | Accesos / Accesos | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3098 | $0.000720 |
| EV-08 | `ajuste` | Software / Software | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3092 | $0.000717 |
| EV-09 | `ajuste` | Accesos / Accesos | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3094 | $0.000720 |
| EV-10 | `ajuste` | Software / Software | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3072 | $0.000707 |
| EV-11 | `ajuste` | Hardware / Hardware | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3108 | $0.000746 |
| EV-12 | `ajuste` | Red / Red | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3106 | $0.000743 |
| EV-13 | `ajuste` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1546 | $0.000407 |
| EV-14 | `nuevo` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3108 | $0.000731 |
| EV-15 | `nuevo` | Software / Software | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3095 | $0.000717 |
| EV-16 | `nuevo` | Hardware / Hardware | Usuario / Usuario | Baja / Media | P4 / P3 | ❌ Fallo | 3086 | $0.000716 |
| EV-17 | `nuevo` | Accesos / Accesos | Usuario / Departamento | Media / Alta | P3 / P1 | ❌ Fallo | 3119 | $0.000740 |
| EV-18 | `nuevo` | Red / Red | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 3127 | $0.000761 |
| EV-19 | `validacion` | Hardware / Accesos | Departamento / Departamento | Alta / Alta | P1 / P1 | ❌ Fallo | 3117 | $0.000738 |
| EV-20 | `validacion` | Software / Software | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3095 | $0.000721 |
| EV-21 | `validacion` | Red / Red | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3093 | $0.000725 |
| EV-22 | `validacion` | Accesos / Accesos | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3091 | $0.000722 |
| EV-23 | `validacion` | Hardware / Hardware | Usuario / Usuario | Baja / Media | P4 / P3 | ❌ Fallo | 3090 | $0.000717 |
| EV-24 | `validacion` | Software / Software | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 3120 | $0.000746 |
| EV-25 | `validacion` | Red / Red | Departamento / Departamento | Baja / Media | P3 / P2 | ❌ Fallo | 3118 | $0.000739 |
| EV-26 | `validacion` | Accesos / Accesos | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3111 | $0.000732 |
| EV-27 | `validacion` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1536 | $0.000394 |
| EV-28 | `validacion` | Hardware / Hardware | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3112 | $0.000730 |
