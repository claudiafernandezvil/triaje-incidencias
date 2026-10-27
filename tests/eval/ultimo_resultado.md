# Último Resultado de Evaluación del Clasificador

- **Fecha (UTC):** 2026-10-27 08:47:58
- **Modelo evaluado:** `openai/gpt-5.4-nano-2026-03-17`
- **Total de casos evaluados:** 58

## 1. Resumen de Aciertos

| Métrica | Aciertos | Porcentaje |
| :--- | :---: | :---: |
| **Casos totalmente correctos (Global)** | 48/58 | 82.8% |
| Conjunto `ajuste` | 12/13 | 92.3% |
| Conjunto `nuevo` | 3/5 | 60.0% |
| Conjunto `validacion` | 9/10 | 90.0% |
| Conjunto `validacion_2` | 24/30 | 80.0% |

### Precisión por Campo (Casos Estándar)

| Campo | Aciertos | Porcentaje |
| :--- | :---: | :---: |
| Categoría | 53/54 | 98.1% |
| Impacto | 53/54 | 98.1% |
| Urgencia | 45/54 | 83.3% |
| Prioridad | 45/54 | 83.3% |

## 2. Consumo y Costes FinOps

| Concepto | Cantidad |
| :--- | :---: |
| Tokens de entrada (prompt) | 170,185 |
| Tokens de salida (completion) | 6,017 |
| Tokens totales | 176,202 |
| Coste total estimado | **$0.041558 USD** |

## 3. Tabla de Fallos

| ID | Conjunto | Incidencia | Discrepancias (Esperado vs Obtenido) |
| :---: | :---: | :--- | :--- |
| EV-05 | `ajuste` | Mi ratón inalámbrico se desconecta cada rato, aunq... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P4', obtenido='P3' |
| EV-16 | `nuevo` | El ventilador del portátil hace un ruido raro, per... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P4', obtenido='P3' |
| EV-17 | `nuevo` | A una compañera nueva le falta acceso a la carpeta... | Impacto: esperado='Usuario', obtenido='Departamento'<br>Urgencia: esperado='Media', obtenido='Alta'<br>Prioridad: esperado='P3', obtenido='P1' |
| EV-19 | `validacion` | El lector de tarjetas de la entrada no funciona y ... | Categoría: esperado='Hardware', obtenido='Red' |
| EV-30 | `validacion_2` | La VPN me desconecta cada media hora; vuelvo a con... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P4', obtenido='P3' |
| EV-40 | `validacion_2` | El CRM va muy lento para todo el equipo comercial,... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P3', obtenido='P2' |
| EV-43 | `validacion_2` | La pantalla de mi portátil se ha roto y no veo nad... | Urgencia: esperado='Alta', obtenido='Media'<br>Prioridad: esperado='P2', obtenido='P3' |
| EV-48 | `validacion_2` | El escáner de administración no funciona y nadie d... | Urgencia: esperado='Media', obtenido='Alta'<br>Prioridad: esperado='P2', obtenido='P1' |
| EV-50 | `validacion_2` | He olvidado mi contraseña y no puedo iniciar sesió... | Urgencia: esperado='Alta', obtenido='Media'<br>Prioridad: esperado='P2', obtenido='P3' |
| EV-51 | `validacion_2` | Necesito permiso de lectura en la carpeta de proye... | Urgencia: esperado='Media', obtenido='Baja'<br>Prioridad: esperado='P3', obtenido='P4' |

## 4. Detalle de Ejecución por Caso

| ID | Conjunto | Categoría (Esp / Obt) | Impacto (Esp / Obt) | Urgencia (Esp / Obt) | Prioridad (Esp / Obt) | Estado | Tokens | Coste ($) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| EV-01 | `ajuste` | Red / Red | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3127 | $0.000725 |
| EV-02 | `ajuste` | Hardware / Hardware | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3110 | $0.000719 |
| EV-03 | `ajuste` | Accesos / Accesos | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3125 | $0.000735 |
| EV-04 | `ajuste` | Software / Software | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3119 | $0.000724 |
| EV-05 | `ajuste` | Hardware / Hardware | Usuario / Usuario | Baja / Media | P4 / P3 | ❌ Fallo | 3122 | $0.000736 |
| EV-06 | `ajuste` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3108 | $0.000724 |
| EV-07 | `ajuste` | Accesos / Accesos | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3115 | $0.000727 |
| EV-08 | `ajuste` | Software / Software | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3103 | $0.000716 |
| EV-09 | `ajuste` | Accesos / Accesos | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3128 | $0.000747 |
| EV-10 | `ajuste` | Software / Software | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3102 | $0.000730 |
| EV-11 | `ajuste` | Hardware / Hardware | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3130 | $0.000758 |
| EV-12 | `ajuste` | Red / Red | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3126 | $0.000753 |
| EV-13 | `ajuste` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1556 | $0.000412 |
| EV-14 | `nuevo` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3113 | $0.000722 |
| EV-15 | `nuevo` | Software / Software | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3116 | $0.000728 |
| EV-16 | `nuevo` | Hardware / Hardware | Usuario / Usuario | Baja / Media | P4 / P3 | ❌ Fallo | 3109 | $0.000730 |
| EV-17 | `nuevo` | Accesos / Accesos | Usuario / Departamento | Media / Alta | P3 / P1 | ❌ Fallo | 3132 | $0.000742 |
| EV-18 | `nuevo` | Red / Red | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 3140 | $0.000762 |
| EV-19 | `validacion` | Hardware / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ❌ Fallo | 3134 | $0.000744 |
| EV-20 | `validacion` | Software / Software | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3101 | $0.000714 |
| EV-21 | `validacion` | Red / Red | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3100 | $0.000719 |
| EV-22 | `validacion` | Accesos / Accesos | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 4807 | $0.001121 |
| EV-23 | `validacion` | Hardware / Hardware | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3107 | $0.000721 |
| EV-24 | `validacion` | Software / Software | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 3136 | $0.000751 |
| EV-25 | `validacion` | Red / Red | Departamento / Departamento | Baja / Baja | P3 / P3 | ✅ OK | 3125 | $0.000731 |
| EV-26 | `validacion` | Accesos / Accesos | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3109 | $0.000715 |
| EV-27 | `validacion` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1533 | $0.000383 |
| EV-28 | `validacion` | Hardware / Hardware | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3127 | $0.000734 |
| EV-29 | `validacion_2` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3135 | $0.000737 |
| EV-30 | `validacion_2` | Red / Red | Usuario / Usuario | Baja / Media | P4 / P3 | ❌ Fallo | 3126 | $0.000747 |
| EV-31 | `validacion_2` | Red / Red | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3118 | $0.000735 |
| EV-32 | `validacion_2` | Red / Red | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 3147 | $0.000773 |
| EV-33 | `validacion_2` | Red / Red | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3120 | $0.000733 |
| EV-34 | `validacion_2` | Red / Red | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3127 | $0.000755 |
| EV-35 | `validacion_2` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3108 | $0.000722 |
| EV-36 | `validacion_2` | Software / Software | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3105 | $0.000727 |
| EV-37 | `validacion_2` | Software / Software | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3119 | $0.000721 |
| EV-38 | `validacion_2` | Software / Software | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3100 | $0.000714 |
| EV-39 | `validacion_2` | Software / Software | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3121 | $0.000722 |
| EV-40 | `validacion_2` | Software / Software | Departamento / Departamento | Baja / Media | P3 / P2 | ❌ Fallo | 3113 | $0.000733 |
| EV-41 | `validacion_2` | Software / Software | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3100 | $0.000721 |
| EV-42 | `validacion_2` | Software / Software | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3106 | $0.000722 |
| EV-43 | `validacion_2` | Hardware / Hardware | Usuario / Usuario | Alta / Media | P2 / P3 | ❌ Fallo | 3126 | $0.000757 |
| EV-44 | `validacion_2` | Hardware / Hardware | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3105 | $0.000723 |
| EV-45 | `validacion_2` | Hardware / Hardware | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3125 | $0.000729 |
| EV-46 | `validacion_2` | Hardware / Hardware | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3111 | $0.000732 |
| EV-47 | `validacion_2` | Hardware / Hardware | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3100 | $0.000729 |
| EV-48 | `validacion_2` | Hardware / Hardware | Departamento / Departamento | Media / Alta | P2 / P1 | ❌ Fallo | 3099 | $0.000713 |
| EV-49 | `validacion_2` | Hardware / Hardware | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 3114 | $0.000747 |
| EV-50 | `validacion_2` | Accesos / Accesos | Usuario / Usuario | Alta / Media | P2 / P3 | ❌ Fallo | 3109 | $0.000734 |
| EV-51 | `validacion_2` | Accesos / Accesos | Usuario / Usuario | Media / Baja | P3 / P4 | ❌ Fallo | 3105 | $0.000723 |
| EV-52 | `validacion_2` | Accesos / Accesos | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3111 | $0.000730 |
| EV-53 | `validacion_2` | Accesos / Accesos | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 3126 | $0.000728 |
| EV-54 | `validacion_2` | Accesos / Accesos | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 3119 | $0.000734 |
| EV-55 | `validacion_2` | Accesos / Accesos | Usuario / Usuario | Baja / Baja | P4 / P4 | ✅ OK | 3118 | $0.000729 |
| EV-56 | `validacion_2` | Accesos / Accesos | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 3120 | $0.000744 |
| EV-57 | `validacion_2` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1554 | $0.000408 |
| EV-58 | `validacion_2` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1555 | $0.000410 |
