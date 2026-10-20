"""Herramienta de consulta de estadísticas sobre el historial de incidencias resueltas."""
 
import csv
from collections import Counter
from pathlib import Path
 
from app.tools import calcular_prioridad
 
RUTA_HISTORIAL = (
    Path(__file__).resolve().parent.parent / "data" / "incidencias.csv"
)
CATEGORIAS_VALIDAS = ("Red", "Software", "Hardware", "Accesos")
MAX_EJEMPLOS = 5
 
 
def _leer_historial(ruta: Path = RUTA_HISTORIAL) -> list[dict]:
    """Lee el CSV del historial y devuelve una lista de filas."""
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
 
 
def estadisticas_historial(categoria: str = "") -> dict:
    """Devuelve estadísticas del historial de incidencias de TI ya resueltas.
 
    Úsala para responder preguntas como cuántas incidencias hay en el historial,
    cómo se reparten por categoría, impacto, urgencia o prioridad, o para ver
    ejemplos de incidencias resueltas de una categoría.
 
    Args:
        categoria: Opcional. Red, Software, Hardware o Accesos para filtrar por
            categoría. Si se deja vacío, se usan todas las incidencias.
 
    Returns:
        Un diccionario con el total de incidencias, los recuentos por categoría,
        impacto, urgencia y prioridad, y hasta 5 ejemplos (id y descripción).
        Si la categoría no es válida, devuelve un diccionario con la clave 'error'.
    """
    filas = _leer_historial()
 
    filtro = (categoria or "").strip()
    if filtro:
        filtro = filtro.capitalize()
        if filtro not in CATEGORIAS_VALIDAS:
            return {
                "error": (
                    f"Categoría '{categoria}' no válida. "
                    f"Usa una de: {', '.join(CATEGORIAS_VALIDAS)}."
                )
            }
        filas = [f for f in filas if f["categoria"] == filtro]
 
    prioridades: Counter = Counter()
    for fila in filas:
        resultado = calcular_prioridad(fila["impacto"], fila["urgencia"])
        prioridades[resultado.get("prioridad", "desconocida")] += 1
 
    return {
        "filtro_categoria": filtro or "todas",
        "total": len(filas),
        "por_categoria": dict(Counter(f["categoria"] for f in filas)),
        "por_impacto": dict(Counter(f["impacto"] for f in filas)),
        "por_urgencia": dict(Counter(f["urgencia"] for f in filas)),
        "por_prioridad": dict(sorted(prioridades.items())),
        "ejemplos": [
            {"id": f["id"], "descripcion": f["descripcion"]}
            for f in filas[:MAX_EJEMPLOS]
        ],
    }