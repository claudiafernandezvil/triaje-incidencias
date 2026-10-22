"""Herramientas para el agente de triaje de incidencias.
 
Este módulo define las herramientas que el agente ADK utiliza para:
1. Calcular la prioridad de una incidencia según una matriz fija de impacto y urgencia.
2. Buscar incidencias resueltas similares en la base de datos SQLite (tabla incidencias_resueltas)
   usando coincidencia de palabras.
"""
 
from __future__ import annotations
 
import re
import sqlite3
from typing import Any
 
from app.db import conectar
 
# Matriz de prioridad fija
MATRIZ_PRIORIDAD: dict[tuple[str, str], str] = {
    ("Departamento", "Alta"): "P1",
    ("Departamento", "Media"): "P2",
    ("Departamento", "Baja"): "P3",
    ("Usuario", "Alta"): "P2",
    ("Usuario", "Media"): "P3",
    ("Usuario", "Baja"): "P4",
}
 
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
        al acceder a la base de datos, incluye una clave 'error'.
    """
    if not isinstance(descripcion, str) or not isinstance(categoria, str):
        return {
            "error": "Los parámetros 'descripcion' y 'categoria' deben ser cadenas de texto.",
            "incidencias": [],
        }
 
    categoria_busqueda = categoria.strip().lower()
    palabras_query = _extraer_palabras(descripcion)
 
    candidatos: list[dict[str, Any]] = []
 
    try:
        with conectar() as conexion:
            filas = conexion.execute(
                "SELECT id, descripcion, solucion FROM incidencias_resueltas "
                "WHERE lower(categoria) = ?",
                (categoria_busqueda,),
            ).fetchall()
    except sqlite3.Error as e:
        return {
            "error": f"Error al consultar la base de datos de incidencias: {e}",
            "incidencias": [],
        }
 
    for fila in filas:
        desc_fila = fila["descripcion"] or ""
        coincidencias = len(palabras_query.intersection(_extraer_palabras(desc_fila)))
        candidatos.append({
            "id": fila["id"],
            "descripcion": desc_fila,
            "solucion": fila["solucion"] or "",
            "coincidencias": coincidencias,
        })
 
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