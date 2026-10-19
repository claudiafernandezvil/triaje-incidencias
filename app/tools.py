"""Herramientas para el agente de triaje de incidencias.

Este módulo define las herramientas que el agente ADK utiliza para:
1. Calcular la prioridad de una incidencia según una matriz fija de impacto y urgencia.
2. Buscar incidencias resueltas similares en una base de datos local (CSV) usando coincidencia de palabras.
"""

from __future__ import annotations

import csv
from pathlib import Path
import re
from typing import Any

# Matriz de prioridad fija
MATRIZ_PRIORIDAD: dict[tuple[str, str], str] = {
    ("Departamento", "Alta"): "P1",
    ("Departamento", "Media"): "P2",
    ("Departamento", "Baja"): "P3",
    ("Usuario", "Alta"): "P2",
    ("Usuario", "Media"): "P3",
    ("Usuario", "Baja"): "P4",
}

# Ubicación por defecto del archivo de incidencias
DEFAULT_CSV_PATH = Path("data/incidencias.csv")


def _obtener_ruta_csv() -> Path:
    """Devuelve la ruta absoluta o relativa válida para data/incidencias.csv."""
    if DEFAULT_CSV_PATH.exists():
        return DEFAULT_CSV_PATH
    # Si se ejecuta desde un subdirectorio (ej. tests/), buscar relativo a la raíz
    raiz_proyecto = Path(__file__).resolve().parent.parent / "data" / "incidencias.csv"
    return raiz_proyecto


def _extraer_palabras(texto: str) -> set[str]:
    """Extrae el conjunto de palabras alfanuméricas en minúsculas de un texto."""
    if not texto:
        return set()
    return set(re.findall(r"\b\w+\b", texto.lower()))


def calcular_prioridad(impacto: str, urgencia: str) -> dict[str, Any]:
    """Calcula el nivel de prioridad (P1 a P4) de una incidencia técnica.

    Aplica una matriz estricta de triaje basada en el impacto del incidente
    y la urgencia del reporte:
    - Departamento + Alta = P1
    - Departamento + Media = P2
    - Departamento + Baja = P3
    - Usuario + Alta = P2
    - Usuario + Media = P3
    - Usuario + Baja = P4

    Args:
        impacto: Alcance de la incidencia. Valores aceptados: 'Usuario' o 'Departamento'.
        urgencia: Nivel de urgencia operativa. Valores aceptados: 'Alta', 'Media' o 'Baja'.

    Returns:
        Un diccionario con la prioridad calculada (ej. {'prioridad': 'P1', ...})
        o con una descripción del problema si los valores son inválidos (ej. {'error': '...'}).
    """
    if not isinstance(impacto, str) or not isinstance(urgencia, str):
        return {
            "error": (
                f"Parámetros inválidos: impacto y urgencia deben ser cadenas de texto. "
                f"Recibido impacto={type(impacto).__name__}, urgencia={type(urgencia).__name__}."
            )
        }

    impacto_norm = impacto.strip().capitalize()
    urgencia_norm = urgencia.strip().capitalize()

    prioridad = MATRIZ_PRIORIDAD.get((impacto_norm, urgencia_norm))
    if not prioridad:
        return {
            "error": (
                f"Valores no válidos: impacto='{impacto}' (debe ser 'Usuario' o 'Departamento') "
                f"y urgencia='{urgencia}' (debe ser 'Alta', 'Media' o 'Baja')."
            )
        }

    return {
        "prioridad": prioridad,
        "impacto": impacto_norm,
        "urgencia": urgencia_norm,
    }


def buscar_incidencias_similares(
    descripcion: str,
    categoria: str,
    max_resultados: int = 3,
) -> dict[str, Any]:
    """Busca incidencias resueltas similares en el histórico a partir de la descripción y categoría.

    Filtra las incidencias históricas por la categoría indicada y las ordena
    de mayor a menor según la cantidad de palabras en común con la descripción recibida,
    sin utilizar modelos de IA ni dependencias externas.

    Args:
        descripcion: Texto descriptivo del problema o incidencia reportada.
        categoria: Categoría de la incidencia para filtrar (ej. 'Red', 'Software', 'Hardware', 'Accesos').
        max_resultados: Número máximo de incidencias similares a devolver (por defecto 3).

    Returns:
        Un diccionario con la lista de incidencias más parecidas bajo la clave 'incidencias',
        donde cada elemento contiene 'id', 'descripcion' y 'solucion'. Si ocurre un error
        o no existe el archivo de datos, incluye una clave 'error'.
    """
    if not isinstance(descripcion, str) or not isinstance(categoria, str):
        return {
            "error": "Los parámetros 'descripcion' y 'categoria' deben ser cadenas de texto.",
            "incidencias": [],
        }

    ruta_csv = _obtener_ruta_csv()
    if not ruta_csv.exists():
        return {
            "error": f"No se encontró el archivo de incidencias en {ruta_csv}.",
            "incidencias": [],
        }

    categoria_busqueda = categoria.strip().lower()
    palabras_query = _extraer_palabras(descripcion)

    candidatos: list[dict[str, Any]] = []

    try:
        with open(ruta_csv, mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            for fila in lector:
                cat_fila = fila.get("categoria", "").strip().lower()
                if cat_fila != categoria_busqueda:
                    continue

                desc_fila = fila.get("descripcion", "")
                palabras_fila = _extraer_palabras(desc_fila)
                coincidencias = len(palabras_query.intersection(palabras_fila))

                candidatos.append({
                    "id": fila.get("id", ""),
                    "descripcion": desc_fila,
                    "solucion": fila.get("solucion", ""),
                    "coincidencias": coincidencias,
                })
    except Exception as e:
        return {
            "error": f"Error al leer el archivo de incidencias: {e}",
            "incidencias": [],
        }

    # Filtrar aquellos con al menos una coincidencia léxica si hay palabras en la consulta
    if palabras_query:
        candidatos = [c for c in candidatos if c["coincidencias"] > 0]

    # Ordenar de mayor a menor coincidencias
    candidatos.sort(key=lambda x: x["coincidencias"], reverse=True)

    # Limitar a max_resultados y omitir el campo auxiliar 'coincidencias' en la salida
    resultados_finales = [
        {
            "id": c["id"],
            "descripcion": c["descripcion"],
            "solucion": c["solucion"],
        }
        for c in candidatos[: max(0, max_resultados)]
    ]

    return {
        "incidencias": resultados_finales,
        "total": len(resultados_finales),
    }
