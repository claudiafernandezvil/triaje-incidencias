#!/usr/bin/env python3
"""Script para generar el informe de costes y consumo FinOps a partir de logs/costes.csv.
 
Distingue dos tipos de sesiones:
- Incidencias completas: sesiones en las que ha intervenido el agente redactor
  (coordinador + cadena de triaje). Son las que se usan para el coste por
  incidencia y la proyección mensual.
- Otras sesiones: evaluaciones (que solo ejecutan el clasificador), consultas
  sobre el historial, saludos, etc. Se cuentan en el gasto total, pero no en
  el coste por incidencia.
"""
 
import csv
import os
from collections import defaultdict
from pathlib import Path
 
from dotenv import load_dotenv
 
# Cargar variables de entorno si existen
load_dotenv()
 
CSV_PATH = Path(os.getenv("RUTA_LOGS_COSTES", "logs/costes.csv"))
DEFAULT_PRESUPUESTO_TOTAL_USD = 5.0
AGENTE_FINAL_TRIAJE = "redactor"
 
 
def generar_informe(ruta_csv: Path = CSV_PATH) -> None:
    """Lee el CSV de costes y genera el informe resumido por consola."""
    print("=" * 65)
    print("           INFORME DE CONTROL DE COSTES (FINOPS)")
    print("=" * 65)
 
    try:
        presupuesto_total = float(
            os.getenv("PRESUPUESTO_TOTAL_USD", str(DEFAULT_PRESUPUESTO_TOTAL_USD))
        )
    except ValueError:
        presupuesto_total = DEFAULT_PRESUPUESTO_TOTAL_USD
 
    if not ruta_csv.exists() or ruta_csv.stat().st_size == 0:
        print(f"\nNo se encontraron registros de costes en '{ruta_csv}'.")
        print(f"Presupuesto asignado: ${presupuesto_total:.2f} USD")
        print("Gasto acumulado: $0.0000 USD (0.00% consumido)\n")
        print("=" * 65)
        return
 
    gasto_total = 0.0
    coste_por_sesion = defaultdict(float)
    tokens_por_sesion = defaultdict(int)
    coste_sesion_agente = defaultdict(lambda: defaultdict(float))
 
    coste_por_agente = defaultdict(float)
    tokens_in_por_agente = defaultdict(int)
    tokens_out_por_agente = defaultdict(int)
    llamadas_por_agente = defaultdict(int)
 
    with open(ruta_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for fila in reader:
            try:
                id_sesion = fila.get("id_sesion") or "desconocida"
                nombre_agente = fila.get("nombre_agente") or "desconocido"
                t_in = int(fila.get("tokens_entrada", 0) or 0)
                t_out = int(fila.get("tokens_salida", 0) or 0)
                coste = float(fila.get("coste_usd", 0.0) or 0.0)
 
                gasto_total += coste
                coste_por_sesion[id_sesion] += coste
                tokens_por_sesion[id_sesion] += (t_in + t_out)
                coste_sesion_agente[id_sesion][nombre_agente] += coste
 
                coste_por_agente[nombre_agente] += coste
                tokens_in_por_agente[nombre_agente] += t_in
                tokens_out_por_agente[nombre_agente] += t_out
                llamadas_por_agente[nombre_agente] += 1
            except (ValueError, TypeError):
                continue
 
    if not coste_por_sesion:
        print(f"\nEl archivo '{ruta_csv}' no contiene llamadas válidas registradas.")
        print("=" * 65)
        return
 
    # Separar incidencias completas (pasan por el redactor) del resto de sesiones
    sesiones_completas = [
        s for s, agentes in coste_sesion_agente.items() if AGENTE_FINAL_TRIAJE in agentes
    ]
    otras_sesiones = [s for s in coste_por_sesion if s not in sesiones_completas]
    hay_completas = bool(sesiones_completas)
    # Si no hay ninguna incidencia completa, se usan todas las sesiones (comportamiento anterior)
    base = sesiones_completas if hay_completas else list(coste_por_sesion)
 
    num_incidencias = len(base)
    coste_incidencias = sum(coste_por_sesion[s] for s in base)
    coste_medio_incidencia = coste_incidencias / num_incidencias
    proyeccion_1000 = coste_medio_incidencia * 1000
    coste_otras = sum(coste_por_sesion[s] for s in otras_sesiones) if hay_completas else 0.0
 
    pct_consumido = (gasto_total / presupuesto_total) * 100 if presupuesto_total > 0 else 0.0
 
    # 1. Estado del presupuesto
    print("\n[1] ESTADO DEL PRESUPUESTO GLOBAL")
    print(f"  * Presupuesto Total:    ${presupuesto_total:.4f} USD")
    print(f"  * Gasto Acumulado:      ${gasto_total:.4f} USD")
    print(f"  * Consumo del Presup.:  {pct_consumido:.2f}%")
    if gasto_total >= presupuesto_total:
        print("  * ALERTA: ¡Presupuesto agotado! Los modelos cortarán nuevas llamadas.")
 
    # 2. Métricas por incidencia
    print("\n[2] MÉTRICAS POR INCIDENCIA")
    if hay_completas:
        print("  (Solo incidencias completas: sesiones que llegan al redactor)")
    else:
        print("  (No hay incidencias completas registradas: se usan todas las sesiones)")
    print(f"  * Total incidencias procesadas: {num_incidencias}")
    print(f"  * Coste medio por incidencia:   ${coste_medio_incidencia:.6f} USD")
    if hay_completas:
        print(
            f"  * Otras sesiones (evaluaciones, consultas, saludos): "
            f"{len(otras_sesiones)} (${coste_otras:.6f} USD)"
        )
 
    # 3. Coste medio de una incidencia por agente
    print("\n[3] COSTE MEDIO DE UNA INCIDENCIA, POR AGENTE")
    print(f"  {'Agente':<16} | {'Coste medio':<12} | {'% del coste':<11}")
    print("  " + "-" * 46)
    coste_agente_base = defaultdict(float)
    for s in base:
        for agente, coste in coste_sesion_agente[s].items():
            coste_agente_base[agente] += coste
    agente_mas_caro = None
    max_coste_medio = -1.0
    for agente, coste_ag in sorted(coste_agente_base.items(), key=lambda x: -x[1]):
        medio = coste_ag / num_incidencias
        pct = (coste_ag / coste_incidencias * 100) if coste_incidencias else 0.0
        if medio > max_coste_medio:
            max_coste_medio = medio
            agente_mas_caro = agente
        print(f"  {agente:<16} | ${medio:<11.6f} | {pct:5.1f}%")
 
    # 4. Desglose global por agente (todas las ejecuciones)
    print("\n[4] DESGLOSE GLOBAL POR AGENTE (todas las ejecuciones)")
    print(f"  {'Agente':<16} | {'Llamadas':<8} | {'Coste Total':<12} | {'Coste Medio':<12} | {'Tokens Medios':<14}")
    print("  " + "-" * 72)
    for agente, llamadas in llamadas_por_agente.items():
        coste_ag = coste_por_agente[agente]
        tokens_totales_ag = tokens_in_por_agente[agente] + tokens_out_por_agente[agente]
        coste_medio_ag = coste_ag / llamadas if llamadas else 0.0
        tokens_medios_ag = tokens_totales_ag / llamadas if llamadas else 0.0
        print(f"  {agente:<16} | {llamadas:<8} | ${coste_ag:<11.6f} | ${coste_medio_ag:<11.6f} | {tokens_medios_ag:<14.1f}")
 
    # 5. Agente más caro
    print("\n[5] AGENTE MÁS CARO (por incidencia)")
    if agente_mas_caro:
        pct_caro = (max_coste_medio / coste_medio_incidencia * 100) if coste_medio_incidencia else 0.0
        print(f"  * {agente_mas_caro}: ${max_coste_medio:.6f} USD por incidencia ({pct_caro:.1f}% del coste)")
 
    # 6. Proyección mensual
    print("\n[6] PROYECCIÓN DE ESCALABILIDAD")
    print(f"  * Proyección para 1.000 incidencias/mes: ${proyeccion_1000:.2f} USD/mes")
    print("=" * 65 + "\n")
 
 
if __name__ == "__main__":
    generar_informe()