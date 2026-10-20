# Último Resultado de Evaluación del Clasificador

- **Fecha (UTC):** 2026-10-20 08:13:12
- **Modelo evaluado:** `openai/gpt-5.4-nano-2026-03-17`
- **Total de casos evaluados:** 28

## 1. Resumen de Aciertos

| Métrica | Aciertos | Porcentaje |
| :--- | :---: | :---: |
| **Casos totalmente correctos (Global)** | 24/28 | 85.7% |
| Conjunto `ajuste` | 12/13 | 92.3% |
| Conjunto `nuevo` | 3/5 | 60.0% |
| Conjunto `validacion` | 9/10 | 90.0% |

### Precisión por Campo (Casos Estándar)

| Campo | Aciertos | Porcentaje |
| :--- | :---: | :---: |
| Categoría | 25/26 | 96.2% |
| Impacto | 25/26 | 96.2% |
| Urgencia | 23/26 | 88.5% |
| Prioridad | 23/26 | 88.5% |

## 2. Consumo y Costes FinOps

| Concepto | Cantidad |
| :--- | :---: |
| Tokens de entrada (prompt) | 81,304 |
| Tokens de salida (completion) | 2,880 |
| Tokens totales | 84,184 |
| Coste total estimado | **$0.019861 USD** |

## 3. Tabla de Fallos

| ID | Conjunto | Incidencia | Discrepancias (Esperado vs Obtenido) |
| :---: | :---: | :--- | :--- |
| EV-05 | `ajuste` | Mi ratón inalámbrico se desconecta cada rato, aunq... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P4', obtenido='P3' |
| EV-16 | `nuevo` | El ventilador del portátil hace un ruido raro, per... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P4', obtenido='P3' |
| EV-17 | `nuevo` | A una compañera nueva le falta acceso a la carpeta... | Impacto: esperado='Usuario', obtenido='Departamento'<br>Urgencia: esperado='Media', obtenido='Alta'<br>Prioridad: esperado='P3', obtenido='P1' |
| EV-19 | `validacion` | El lector de tarjetas de la entrada no funciona y ... | Categoría: esperado='Hardware', obtenido='Accesos' |

## 4. Detalle de Ejecución por Caso

| ID | Conjunto | Categoría (Esp / Obt) | Impacto (Esp / Obt) | Urgencia (Esp / Obt) | Prioridad (Esp / Obt) | Estado | Tokens | Coste ($) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| EV-01 | `ajuste` | Red / Red | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3124 | $0.000721 |
| EV-02 | `ajuste` | Hardware / Hardware | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3113 | $0.000722 |
| EV-03 | `ajuste` | Accesos / Accesos | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3113 | $0.000720 |
| EV-04 | `ajuste` | Software / Software | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3113 | $0.000716 |
| EV-05 | `ajuste` | Hardware / Hardware | Usuario / Usuario | Baja / Media | P4 / P3 | ❌ Fallo | 3124 | $0.000738 |
| EV-06 | `ajuste` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3102 | $0.000717 |
| EV-07 | `ajuste` | Accesos / Accesos | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3116 | $0.000728 |
| EV-08 | `ajuste` | Software / Software | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3101 | $0.000714 |
| EV-09 | `ajuste` | Accesos / Accesos | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3134 | $0.000755 |
| EV-10 | `ajuste` | Software / Software | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3098 | $0.000725 |
| EV-11 | `ajuste` | Hardware / Hardware | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3118 | $0.000743 |
| EV-12 | `ajuste` | Red / Red | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3114 | $0.000738 |
| EV-13 | `ajuste` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1557 | $0.000413 |
| EV-14 | `nuevo` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3116 | $0.000726 |
| EV-15 | `nuevo` | Software / Software | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3116 | $0.000728 |
| EV-16 | `nuevo` | Hardware / Hardware | Usuario / Usuario | Baja / Media | P4 / P3 | ❌ Fallo | 3102 | $0.000721 |
| EV-17 | `nuevo` | Accesos / Accesos | Usuario / Departamento | Media / Alta | P3 / P1 | ❌ Fallo | 3130 | $0.000739 |
| EV-18 | `nuevo` | Red / Red | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 3140 | $0.000762 |
| EV-19 | `validacion` | Hardware / Accesos | Departamento / Departamento | Alta / Alta | P1 / P1 | ❌ Fallo | 3137 | $0.000748 |
| EV-20 | `validacion` | Software / Software | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3101 | $0.000714 |
| EV-21 | `validacion` | Red / Red | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3104 | $0.000724 |
| EV-22 | `validacion` | Accesos / Accesos | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3133 | $0.000760 |
| EV-23 | `validacion` | Hardware / Hardware | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3110 | $0.000725 |
| EV-24 | `validacion` | Software / Software | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 3141 | $0.000757 |
| EV-25 | `validacion` | Red / Red | Departamento / Departamento | Baja / Baja | P3 / P3 | ✅ OK | 3132 | $0.000740 |
| EV-26 | `validacion` | Accesos / Accesos | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3112 | $0.000719 |
| EV-27 | `validacion` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1557 | $0.000413 |
| EV-28 | `validacion` | Hardware / Hardware | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3126 | $0.000732 |
