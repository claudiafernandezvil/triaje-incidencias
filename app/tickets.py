"""Function tools para registrar y consultar los tickets de incidencias abiertas.
 
Los tickets se guardan en un CSV cuya ruta se puede cambiar con la variable de
entorno RUTA_TICKETS (por defecto data/tickets_registrados.csv). La ruta se lee
en cada llamada, de modo que los tests y las evaluaciones pueden usar un fichero
aparte sin afectar a los tickets reales.
"""
 
import csv
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
 
from app.tools import calcular_prioridad
 
RUTA_TICKETS_POR_DEFECTO = (
    Path(__file__).resolve().parent.parent / "data" / "tickets_registrados.csv"
)
CAMPOS = ["id", "fecha", "descripcion", "categoria", "impacto", "urgencia", "prioridad", "estado"]
CATEGORIAS_VALIDAS = ("Red", "Software", "Hardware", "Accesos")
IMPACTOS_VALIDOS = ("Usuario", "Departamento")
URGENCIAS_VALIDAS = ("Alta", "Media", "Baja")
PRIORIDADES_VALIDAS = ("P1", "P2", "P3", "P4")
MAX_TICKETS_LISTADOS = 10
 
 
def _ruta_tickets() -> Path:
    """Devuelve la ruta del CSV de tickets (configurable con RUTA_TICKETS)."""
    return Path(os.getenv("RUTA_TICKETS", str(RUTA_TICKETS_POR_DEFECTO)))
 
 
def _leer_tickets() -> list[dict]:
    ruta = _ruta_tickets()
    if not ruta.exists() or ruta.stat().st_size == 0:
        return []
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
 
 
def _normalizar(valor: str) -> str:
    return (valor or "").strip().capitalize()
 
 
def registrar_incidencia(
    descripcion: str, categoria: str, impacto: str, urgencia: str
) -> dict:
    """Registra una incidencia nueva como ticket abierto y devuelve su número.
 
    Úsala una sola vez por incidencia, después de clasificarla. La prioridad se
    calcula automáticamente a partir del impacto y la urgencia.
 
    Args:
        descripcion: Texto original de la incidencia tal como lo escribió el usuario.
        categoria: Red, Software, Hardware o Accesos.
        impacto: Usuario o Departamento.
        urgencia: Alta, Media o Baja.
 
    Returns:
        Un diccionario con el id del ticket (por ejemplo, 'TCK-0001'), la
        prioridad calculada, el estado ('abierta') y la fecha. Si algún valor no
        es válido, devuelve un diccionario con la clave 'error' y no registra nada.
    """
    descripcion = (descripcion or "").strip()
    categoria = _normalizar(categoria)
    impacto = _normalizar(impacto)
    urgencia = _normalizar(urgencia)
 
    if not descripcion:
        return {"error": "La descripción de la incidencia está vacía."}
    if categoria not in CATEGORIAS_VALIDAS:
        return {"error": f"Categoría '{categoria}' no válida. Usa una de: {', '.join(CATEGORIAS_VALIDAS)}."}
    if impacto not in IMPACTOS_VALIDOS:
        return {"error": f"Impacto '{impacto}' no válido. Usa una de: {', '.join(IMPACTOS_VALIDOS)}."}
    if urgencia not in URGENCIAS_VALIDAS:
        return {"error": f"Urgencia '{urgencia}' no válida. Usa una de: {', '.join(URGENCIAS_VALIDAS)}."}
 
    resultado_prioridad = calcular_prioridad(impacto, urgencia)
    prioridad = resultado_prioridad.get("prioridad")
    if prioridad not in PRIORIDADES_VALIDAS:
        return {"error": f"No se pudo calcular la prioridad: {resultado_prioridad}"}
 
    existentes = _leer_tickets()
    ticket = {
        "id": f"TCK-{len(existentes) + 1:04d}",
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "descripcion": descripcion,
        "categoria": categoria,
        "impacto": impacto,
        "urgencia": urgencia,
        "prioridad": prioridad,
        "estado": "abierta",
    }
 
    ruta = _ruta_tickets()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    escribir_cabecera = not ruta.exists() or ruta.stat().st_size == 0
    with open(ruta, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        if escribir_cabecera:
            writer.writeheader()
        writer.writerow(ticket)
 
    return {
        "id": ticket["id"],
        "prioridad": prioridad,
        "estado": ticket["estado"],
        "fecha": ticket["fecha"],
    }
 
 
def consultar_tickets(categoria: str = "", prioridad: str = "") -> dict:
    """Consulta los tickets de incidencias registrados (incidencias abiertas).
 
    Úsala para responder preguntas sobre las incidencias registradas por el
    sistema, por ejemplo cuántas incidencias P1 hay abiertas o cuáles son las
    últimas incidencias de Red. No incluye el historial de incidencias resueltas.
 
    Args:
        categoria: Opcional. Red, Software, Hardware o Accesos para filtrar.
        prioridad: Opcional. P1, P2, P3 o P4 para filtrar.
 
    Returns:
        Un diccionario con el total de tickets que cumplen el filtro, su reparto
        por prioridad y por categoría, y los 10 más recientes (id, fecha,
        categoría, prioridad, estado y descripción).
    """
    tickets = _leer_tickets()
 
    filtro_cat = _normalizar(categoria)
    if filtro_cat:
        if filtro_cat not in CATEGORIAS_VALIDAS:
            return {"error": f"Categoría '{categoria}' no válida. Usa una de: {', '.join(CATEGORIAS_VALIDAS)}."}
        tickets = [t for t in tickets if t["categoria"] == filtro_cat]
 
    filtro_pri = (prioridad or "").strip().upper()
    if filtro_pri:
        if filtro_pri not in PRIORIDADES_VALIDAS:
            return {"error": f"Prioridad '{prioridad}' no válida. Usa una de: {', '.join(PRIORIDADES_VALIDAS)}."}
        tickets = [t for t in tickets if t["prioridad"] == filtro_pri]
 
    recientes = list(reversed(tickets))[:MAX_TICKETS_LISTADOS]
    return {
        "filtro_categoria": filtro_cat or "todas",
        "filtro_prioridad": filtro_pri or "todas",
        "total": len(tickets),
        "por_prioridad": dict(sorted(Counter(t["prioridad"] for t in tickets).items())),
        "por_categoria": dict(Counter(t["categoria"] for t in tickets)),
        "tickets_recientes": [
            {
                "id": t["id"],
                "fecha": t["fecha"],
                "categoria": t["categoria"],
                "prioridad": t["prioridad"],
                "estado": t["estado"],
                "descripcion": t["descripcion"],
            }
            for t in recientes
        ],
    }