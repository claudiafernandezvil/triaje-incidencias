# Último Resultado de Evaluación del Clasificador

- **Fecha (UTC):** 2026-10-19 10:53:48
- **Modelo evaluado:** `openai/gpt-5.4-nano-2026-03-17`
- **Total de casos evaluados:** 18

## 1. Resumen de Aciertos

| Métrica | Aciertos | Porcentaje |
| :--- | :---: | :---: |
| **Casos totalmente correctos (Global)** | 11/18 | 61.1% |
| Conjunto `ajuste` | 9/13 | 69.2% |
| Conjunto `nuevo` | 2/5 | 40.0% |

### Precisión por Campo (Casos Estándar)

| Campo | Aciertos | Porcentaje |
| :--- | :---: | :---: |
| Categoría | 16/17 | 94.1% |
| Impacto | 12/17 | 70.6% |
| Urgencia | 11/17 | 64.7% |
| Prioridad | 10/17 | 58.8% |

## 2. Consumo y Costes FinOps

| Concepto | Cantidad |
| :--- | :---: |
| Tokens de entrada (prompt) | 36,449 |
| Tokens de salida (completion) | 1,790 |
| Tokens totales | 38,239 |
| Coste total estimado | **$0.009527 USD** |

## 3. Tabla de Fallos

| ID | Conjunto | Incidencia | Discrepancias (Esperado vs Obtenido) |
| :---: | :---: | :--- | :--- |
| EV-03 | `ajuste` | Me salta un aviso de que mi contraseña caduca en 3... | Impacto: esperado='Usuario', obtenido='None'<br>Urgencia: esperado='Baja', obtenido='None'<br>Prioridad: esperado='P4', obtenido='None' |
| EV-05 | `ajuste` | Mi ratón inalámbrico se desconecta cada rato, aunq... | Urgencia: esperado='Baja', obtenido='Media'<br>Prioridad: esperado='P4', obtenido='P3' |
| EV-11 | `ajuste` | La pantalla del portátil parpadea y a veces se que... | Impacto: esperado='Usuario', obtenido='None'<br>Urgencia: esperado='Media', obtenido='None'<br>Prioridad: esperado='P3', obtenido='None' |
| EV-12 | `ajuste` | Las páginas de la intranet no cargan, pero Google ... | Impacto: esperado='Usuario', obtenido='Departamento'<br>Prioridad: esperado='P3', obtenido='P2' |
| EV-15 | `nuevo` | ¿Me podéis instalar el lector de PDF que usa el re... | Categoría: esperado='Software', obtenido='Accesos'<br>Impacto: esperado='Usuario', obtenido='None'<br>Urgencia: esperado='Baja', obtenido='None'<br>Prioridad: esperado='P4', obtenido='None' |
| EV-16 | `nuevo` | El ventilador del portátil hace un ruido raro, per... | Impacto: esperado='Usuario', obtenido='None'<br>Urgencia: esperado='Baja', obtenido='None'<br>Prioridad: esperado='P4', obtenido='None' |
| EV-17 | `nuevo` | A una compañera nueva le falta acceso a la carpeta... | Urgencia: esperado='Media', obtenido='Alta'<br>Prioridad: esperado='P3', obtenido='P2' |

## 4. Detalle de Ejecución por Caso

| ID | Conjunto | Categoría (Esp / Obt) | Impacto (Esp / Obt) | Urgencia (Esp / Obt) | Prioridad (Esp / Obt) | Estado | Tokens | Coste ($) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| EV-01 | `ajuste` | Red / Red | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 2474 | $0.000593 |
| EV-02 | `ajuste` | Hardware / Hardware | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 2450 | $0.000578 |
| EV-03 | `ajuste` | Accesos / Accesos | Usuario / - | Baja / - | P4 / - | ❌ Fallo | 1242 | $0.000342 |
| EV-04 | `ajuste` | Software / Software | Usuario / Usuario | Alta / Alta | P2 / P2 | ✅ OK | 2454 | $0.000577 |
| EV-05 | `ajuste` | Hardware / Hardware | Usuario / Usuario | Baja / Media | P4 / P3 | ❌ Fallo | 2478 | $0.000615 |
| EV-06 | `ajuste` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 2451 | $0.000588 |
| EV-07 | `ajuste` | Accesos / Accesos | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 2455 | $0.000587 |
| EV-08 | `ajuste` | Software / Software | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 2449 | $0.000583 |
| EV-09 | `ajuste` | Accesos / Accesos | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 2476 | $0.000617 |
| EV-10 | `ajuste` | Software / Software | Usuario / Usuario | Media / Media | P3 / P3 | ✅ OK | 2456 | $0.000607 |
| EV-11 | `ajuste` | Hardware / Hardware | Usuario / - | Media / - | P3 / - | ❌ Fallo | 1257 | $0.000368 |
| EV-12 | `ajuste` | Red / Red | Usuario / Departamento | Media / Media | P3 / P2 | ❌ Fallo | 2484 | $0.000635 |
| EV-13 | `ajuste` | requiere más información / requiere más información | - / - | - / - | - / - | ✅ OK | 1257 | $0.000381 |
| EV-14 | `nuevo` | Red / Red | Departamento / Departamento | Alta / Alta | P1 / P1 | ✅ OK | 2468 | $0.000601 |
| EV-15 | `nuevo` | Software / Accesos | Usuario / - | Baja / - | P4 / - | ❌ Fallo | 1233 | $0.000333 |
| EV-16 | `nuevo` | Hardware / Hardware | Usuario / - | Baja / - | P4 / - | ❌ Fallo | 1230 | $0.000333 |
| EV-17 | `nuevo` | Accesos / Accesos | Usuario / Usuario | Media / Alta | P3 / P2 | ❌ Fallo | 2465 | $0.000593 |
| EV-18 | `nuevo` | Red / Red | Departamento / Departamento | Media / Media | P2 / P2 | ✅ OK | 2460 | $0.000597 |
