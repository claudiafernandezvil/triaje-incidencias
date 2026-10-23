"""Function tools para registrar, consultar y cerrar los tickets de incidencias.
 
Los tickets se guardan en la tabla 'tickets' de la base de datos SQLite
(ver app/db.py; ruta configurable con la variable de entorno RUTA_BD).
"""
 
import re
from collections import Counter
from datetime import datetime
 
from app.db import conectar
from app.tools import calcular_prioridad
 
CATEGORIAS_VALIDAS = ("Red", "Software", "Hardware", "Accesos")
IMPACTOS_VALIDOS = ("Usuario", "Departamento")
URGENCIAS_VALIDAS = ("Alta", "Media", "Baja")
PRIORIDADES_VALIDAS = ("P1", "P2", "P3", "P4")
ESTADOS_VALIDOS = ("abierta", "cerrada", "todas")
PATRON_ID_TICKET = re.compile(r"^TCK-\d{4}$")
LONGITUD_MINIMA_SOLUCION = 10
MAX_TICKETS_LISTADOS = 10
 
 
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
 
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conexion:
        numero = conexion.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] + 1
        id_ticket = f"TCK-{numero:04d}"
        conexion.execute(
            "INSERT INTO tickets "
            "(id, fecha, descripcion, categoria, impacto, urgencia, prioridad, estado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'abierta')",
            (id_ticket, fecha, descripcion, categoria, impacto, urgencia, prioridad),
        )
 
    return {"id": id_ticket, "prioridad": prioridad, "estado": "abierta", "fecha": fecha}
 
 
def consultar_tickets(categoria: str = "", prioridad: str = "", estado: str = "abierta") -> dict:
    """Consulta los tickets de incidencias registrados por el sistema.
 
    Úsala para responder preguntas sobre los tickets, por ejemplo cuántas
    incidencias P1 hay abiertas, cuáles son las últimas de Red o qué tickets
    se han cerrado. No incluye el historial de incidencias resueltas.
 
    Args:
        categoria: Opcional. Red, Software, Hardware o Accesos para filtrar.
        prioridad: Opcional. P1, P2, P3 o P4 para filtrar.
        estado: 'abierta' (por defecto), 'cerrada' o 'todas'.
 
    Returns:
        Un diccionario con el total de tickets que cumplen el filtro, su reparto
        por prioridad, categoría y estado, y los 10 más recientes (id, fecha,
        categoría, prioridad, estado y descripción).
    """
    condiciones: list[str] = []
    parametros: list[str] = []
 
    filtro_cat = _normalizar(categoria)
    if filtro_cat:
        if filtro_cat not in CATEGORIAS_VALIDAS:
            return {"error": f"Categoría '{categoria}' no válida. Usa una de: {', '.join(CATEGORIAS_VALIDAS)}."}
        condiciones.append("categoria = ?")
        parametros.append(filtro_cat)
 
    filtro_pri = (prioridad or "").strip().upper()
    if filtro_pri:
        if filtro_pri not in PRIORIDADES_VALIDAS:
            return {"error": f"Prioridad '{prioridad}' no válida. Usa una de: {', '.join(PRIORIDADES_VALIDAS)}."}
        condiciones.append("prioridad = ?")
        parametros.append(filtro_pri)
 
    filtro_estado = (estado or "abierta").strip().lower()
    if filtro_estado not in ESTADOS_VALIDOS:
        return {"error": f"Estado '{estado}' no válido. Usa uno de: {', '.join(ESTADOS_VALIDOS)}."}
    if filtro_estado != "todas":
        condiciones.append("estado = ?")
        parametros.append(filtro_estado)
 
    consulta = "SELECT id, fecha, descripcion, categoria, prioridad, estado FROM tickets"
    if condiciones:
        consulta += " WHERE " + " AND ".join(condiciones)
    consulta += " ORDER BY id DESC"
 
    with conectar() as conexion:
        tickets = [dict(fila) for fila in conexion.execute(consulta, parametros).fetchall()]
 
    return {
        "filtro_categoria": filtro_cat or "todas",
        "filtro_prioridad": filtro_pri or "todas",
        "filtro_estado": filtro_estado,
        "total": len(tickets),
        "por_prioridad": dict(sorted(Counter(t["prioridad"] for t in tickets).items())),
        "por_categoria": dict(Counter(t["categoria"] for t in tickets)),
        "por_estado": dict(Counter(t["estado"] for t in tickets)),
        "tickets_recientes": tickets[:MAX_TICKETS_LISTADOS],
    }
 
 
def ver_ticket(id_ticket: str) -> dict:
    """Devuelve los datos de un ticket concreto a partir de su identificador.
 
    Úsala antes de cerrar un ticket, para conocer la incidencia original y
    comprobar que la solución propuesta tiene relación con ella.
 
    Args:
        id_ticket: Identificador del ticket, con el formato TCK-0001.
 
    Returns:
        Un diccionario con el id, la fecha, la descripción original, la
        categoría, el impacto, la urgencia, la prioridad, el estado y, si está
        cerrado, la solución y la fecha de cierre. Si el identificador no es
        válido o el ticket no existe, devuelve un diccionario con la clave 'error'.
    """
    id_normalizado = (id_ticket or "").strip().upper()
    if not PATRON_ID_TICKET.match(id_normalizado):
        return {"error": f"Identificador '{id_ticket}' no válido. El formato es TCK-0001."}
 
    with conectar() as conexion:
        ticket = conexion.execute(
            "SELECT id, fecha, descripcion, categoria, impacto, urgencia, prioridad, "
            "estado, fecha_cierre, solucion FROM tickets WHERE id = ?",
            (id_normalizado,),
        ).fetchone()
 
    if ticket is None:
        return {"error": f"No existe ningún ticket con el identificador {id_normalizado}."}
 
    datos = dict(ticket)
    if datos["estado"] != "cerrada":
        datos.pop("fecha_cierre")
        datos.pop("solucion")
    return datos
 
 
def cerrar_ticket(id_ticket: str, solucion: str) -> dict:
    """Cierra un ticket abierto indicando cómo se resolvió, y lo añade al historial.
 
    Úsala cuando un técnico indica que un ticket está resuelto. El ticket pasa a
    estado 'cerrada' y se copia al historial de incidencias resueltas con su
    solución, de modo que el buscador podrá proponer esa solución en futuras
    incidencias parecidas.
 
    Args:
        id_ticket: Identificador del ticket, con el formato TCK-0001.
        solucion: Descripción de cómo se resolvió la incidencia (al menos una frase).
 
    Returns:
        Un diccionario con el id del ticket, el estado 'cerrada', la fecha de
        cierre y la confirmación de que se ha añadido al historial. Si el ticket
        no existe, ya estaba cerrado o falta la solución, devuelve un diccionario
        con la clave 'error' y no cambia nada.
    """
    id_normalizado = (id_ticket or "").strip().upper()
    solucion = (solucion or "").strip()
 
    if not PATRON_ID_TICKET.match(id_normalizado):
        return {"error": f"Identificador '{id_ticket}' no válido. El formato es TCK-0001."}
    if len(solucion) < LONGITUD_MINIMA_SOLUCION:
        return {"error": "Falta la solución o es demasiado breve. Indica cómo se resolvió la incidencia."}
 
    fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conexion:
        ticket = conexion.execute(
            "SELECT id, descripcion, categoria, impacto, urgencia, estado FROM tickets WHERE id = ?",
            (id_normalizado,),
        ).fetchone()
        if ticket is None:
            return {"error": f"No existe ningún ticket con el identificador {id_normalizado}."}
        if ticket["estado"] == "cerrada":
            return {"error": f"El ticket {id_normalizado} ya estaba cerrado."}
 
        # Las dos operaciones van en la misma transacción: o se hacen ambas o ninguna
        conexion.execute(
            "UPDATE tickets SET estado = 'cerrada', fecha_cierre = ?, solucion = ? WHERE id = ?",
            (fecha_cierre, solucion, id_normalizado),
        )
        conexion.execute(
            "INSERT INTO incidencias_resueltas "
            "(id, descripcion, categoria, impacto, urgencia, solucion, origen, fecha_resolucion) "
            "VALUES (?, ?, ?, ?, ?, ?, 'ticket', ?)",
            (
                ticket["id"],
                ticket["descripcion"],
                ticket["categoria"],
                ticket["impacto"],
                ticket["urgencia"],
                solucion,
                fecha_cierre,
            ),
        )
 
    return {
        "id": id_normalizado,
        "estado": "cerrada",
        "fecha_cierre": fecha_cierre,
        "anadido_al_historial": True,
    }