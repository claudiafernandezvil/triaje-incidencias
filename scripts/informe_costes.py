#!/usr/bin/env python3
"""Script para generar el informe de costes y consumo FinOps a partir de logs/costes.csv."""

import csv
import os
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno si existen
load_dotenv()

CSV_PATH = Path(os.getenv("RUTA_LOGS_COSTES", "logs/costes.csv"))
DEFAULT_PRESUPUESTO_TOTAL_USD = 5.0


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

                coste_por_agente[nombre_agente] += coste
                tokens_in_por_agente[nombre_agente] += t_in
                tokens_out_por_agente[nombre_agente] += t_out
                llamadas_por_agente[nombre_agente] += 1
            except (ValueError, TypeError):
                continue

    num_incidencias = len(coste_por_sesion)
    if num_incidencias == 0:
        print(f"\nEl archivo '{ruta_csv}' no contiene llamadas válidas registradas.")
        print("=" * 65)
        return

    pct_consumido = (gasto_total / presupuesto_total) * 100 if presupuesto_total > 0 else 0.0
    coste_medio_incidencia = gasto_total / num_incidencias
    proyeccion_1000 = coste_medio_incidencia * 1000

    # 1. Estado del presupuesto
    print("\n[1] ESTADO DEL PRESUPUESTO GLOBAL")
    print(f"  * Presupuesto Total:    ${presupuesto_total:.4f} USD")
    print(f"  * Gasto Acumulado:      ${gasto_total:.4f} USD")
    print(f"  * Consumo del Presup.:  {pct_consumido:.2f}%")
    if gasto_total >= presupuesto_total:
        print("  * ALERTA: ¡Presupuesto agotado! Los modelos cortarán nuevas llamadas.")

    # 2. Métricas por incidencia
    print("\n[2] MÉTRICAS POR INCIDENCIA")
    print(f"  * Total incidencias procesadas: {num_incidencias}")
    print(f"  * Coste medio por incidencia:   ${coste_medio_incidencia:.6f} USD")

    # 3. Métricas por agente
    print("\n[3] DESGLOSE Y PROMEDIOS POR AGENTE")
    print(f"  {'Agente':<16} | {'Llamadas':<8} | {'Coste Total':<12} | {'Coste Medio':<12} | {'Tokens Medios':<14}")
    print("  " + "-" * 72)

    agente_mas_caro = None
    max_coste_agente = -1.0

    for agente, llamadas in llamadas_por_agente.items():
        coste_ag = coste_por_agente[agente]
        tokens_totales_ag = tokens_in_por_agente[agente] + tokens_out_por_agente[agente]
        coste_medio_ag = coste_ag / llamadas if llamadas else 0.0
        tokens_medios_ag = tokens_totales_ag / llamadas if llamadas else 0.0

        if coste_ag > max_coste_agente:
            max_coste_agente = coste_ag
            agente_mas_caro = agente

        print(f"  {agente:<16} | {llamadas:<8} | ${coste_ag:<11.6f} | ${coste_medio_ag:<11.6f} | {tokens_medios_ag:<14.1f}")

    print("\n[4] AGENTE MÁS CARO")
    if agente_mas_caro:
        print(f"  * {agente_mas_caro} con un gasto acumulado de ${max_coste_agente:.6f} USD")

    # 5. Proyección mensual
    print("\n[5] PROYECCIÓN DE ESCALABILIDAD")
    print(f"  * Proyección para 1.000 incidencias/mes: ${proyeccion_1000:.2f} USD/mes")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    generar_informe()
