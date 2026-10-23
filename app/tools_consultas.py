"""Herramienta de consulta de estadísticas sobre el historial de incidencias resueltas."""
 
from collections import Counter
 
from app.db import conectar
from app.tools import calcular_prioridad
 
CATEGORIAS_VALIDAS = ("Red", "Software", "Hardware", "Accesos")
MAX_EJEMPLOS = 5
 
 
def _leer_historial(categoria: str = "") -> list[dict]:
    """Lee el historial de la base de datos, opcionalmente filtrado por categoría."""
    consulta = "SELECT id, descripcion, categoria, impacto, urgencia, origen FROM incidencias_resueltas"
    parametros: tuple = ()
    if categoria:
        consulta += " WHERE categoria = ?"
        parametros = (categoria,)
    consulta += " ORDER BY id"
    with conectar() as conexion:
        return [dict(fila) for fila in conexion.execute(consulta, parametros).fetchall()]
 
 
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
        impacto, urgencia, prioridad y origen ('historial' para las iniciales,
        'ticket' para las que vienen de tickets cerrados por el sistema), y hasta
        5 ejemplos (id y descripción).
        Si la categoría no es válida, devuelve un diccionario con la clave 'error'.
    """
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
 
    filas = _leer_historial(filtro)
 
    prioridades: Counter = Counter()
    for fila in filas:
        if fila["impacto"] and fila["urgencia"]:
            resultado = calcular_prioridad(fila["impacto"], fila["urgencia"])
            prioridades[resultado.get("prioridad", "desconocida")] += 1
 
    return {
        "filtro_categoria": filtro or "todas",
        "total": len(filas),
        "por_categoria": dict(Counter(f["categoria"] for f in filas)),
        "por_impacto": dict(Counter(f["impacto"] for f in filas if f["impacto"])),
        "por_urgencia": dict(Counter(f["urgencia"] for f in filas if f["urgencia"])),
        "por_prioridad": dict(sorted(prioridades.items())),
        "por_origen": dict(Counter(f["origen"] for f in filas)),
        "ejemplos": [
            {"id": f["id"], "descripcion": f["descripcion"]}
            for f in filas[:MAX_EJEMPLOS]
        ],
    }