"""Tests de las herramientas de tickets (no llaman a OpenAI).
 
Cada test usa una base de datos temporal (ver conftest.py).

"""
 
import pytest
 
from app.db import conectar

from app.tickets import cerrar_ticket, consultar_tickets, registrar_incidencia, ver_ticket

from app.tools import buscar_incidencias_similares
 
 
def _tickets_en_bd() -> list[dict]:

    with conectar() as conexion:

        return [dict(f) for f in conexion.execute("SELECT * FROM tickets ORDER BY id").fetchall()]
 
 
def test_registrar_devuelve_id_y_prioridad_calculada():

    resultado = registrar_incidencia("No hay internet en la sede", "Red", "Departamento", "Alta")

    assert resultado["id"] == "TCK-0001"

    assert resultado["prioridad"] == "P1"

    assert resultado["estado"] == "abierta"
 
 
def test_registrar_guarda_en_base_de_datos():

    registrar_incidencia("La impresora no imprime", "Hardware", "Usuario", "Media")

    tickets = _tickets_en_bd()

    assert len(tickets) == 1

    assert tickets[0]["descripcion"] == "La impresora no imprime"

    assert tickets[0]["categoria"] == "Hardware"

    assert tickets[0]["prioridad"] == "P3"

    assert tickets[0]["estado"] == "abierta"

    assert tickets[0]["fecha_cierre"] is None
 
 
def test_ids_consecutivos():

    primero = registrar_incidencia("Caso 1", "Red", "Usuario", "Baja")

    segundo = registrar_incidencia("Caso 2", "Software", "Usuario", "Alta")

    assert primero["id"] == "TCK-0001"

    assert segundo["id"] == "TCK-0002"
 
 
def test_normaliza_mayusculas_y_espacios():

    resultado = registrar_incidencia("Sin acceso", " accesos ", "usuario", "MEDIA")

    assert resultado["prioridad"] == "P3"

    assert consultar_tickets()["tickets_recientes"][0]["categoria"] == "Accesos"
 
 
@pytest.mark.parametrize(

    "categoria, impacto, urgencia",

    [

        ("Impresoras", "Usuario", "Alta"),

        ("Red", "Empresa", "Alta"),

        ("Red", "Usuario", "Urgentísima"),

    ],

)

def test_valores_invalidos_no_registran(categoria, impacto, urgencia):

    resultado = registrar_incidencia("Algo falla", categoria, impacto, urgencia)

    assert "error" in resultado

    assert _tickets_en_bd() == []
 
 
def test_descripcion_vacia_no_registra():

    resultado = registrar_incidencia("   ", "Red", "Usuario", "Alta")

    assert "error" in resultado

    assert _tickets_en_bd() == []
 
 
def test_consultar_sin_tickets():

    resultado = consultar_tickets()

    assert resultado["total"] == 0

    assert resultado["tickets_recientes"] == []
 
 
def test_consultar_filtra_por_prioridad_y_categoria():

    registrar_incidencia("Caída de red en la sede", "Red", "Departamento", "Alta")  # P1

    registrar_incidencia("VPN lenta", "Red", "Usuario", "Media")  # P3

    registrar_incidencia("ERP caído en contabilidad", "Software", "Departamento", "Alta")  # P1
 
    assert consultar_tickets()["total"] == 3

    assert consultar_tickets(prioridad="P1")["total"] == 2

    assert consultar_tickets(categoria="Red")["total"] == 2

    assert consultar_tickets(categoria="red", prioridad="p1")["total"] == 1
 
 
def test_consultar_ordena_del_mas_reciente_al_mas_antiguo():

    registrar_incidencia("Primero", "Red", "Usuario", "Baja")

    registrar_incidencia("Segundo", "Red", "Usuario", "Baja")

    recientes = consultar_tickets()["tickets_recientes"]

    assert [t["id"] for t in recientes] == ["TCK-0002", "TCK-0001"]
 
 
def test_consultar_filtro_invalido_devuelve_error():

    assert "error" in consultar_tickets(prioridad="P9")

    assert "error" in consultar_tickets(categoria="Impresoras")
 
 
def test_consultar_filtro_estado_invalido_devuelve_error():

    assert "error" in consultar_tickets(estado="pendiente")
 
 
# -------------------------------------------------------------------------

# Cierre de tickets

# -------------------------------------------------------------------------
 
SOLUCION = "Se reinstaló el certificado de la VPN desde el portal de autoservicio."
 
 
def _resueltas_por_id(id_incidencia: str) -> list[dict]:

    with conectar() as conexion:

        return [

            dict(f)

            for f in conexion.execute(

                "SELECT * FROM incidencias_resueltas WHERE id = ?", (id_incidencia,)

            ).fetchall()

        ]
 
 
def test_cerrar_ticket_marca_cerrado_y_guarda_solucion():

    registrar_incidencia("La VPN da error de certificado", "Red", "Usuario", "Alta")

    resultado = cerrar_ticket("TCK-0001", SOLUCION)
 
    assert resultado["estado"] == "cerrada"

    assert resultado["anadido_al_historial"] is True

    ticket = _tickets_en_bd()[0]

    assert ticket["estado"] == "cerrada"

    assert ticket["solucion"] == SOLUCION

    assert ticket["fecha_cierre"] is not None
 
 
def test_cerrar_ticket_lo_anade_al_historial():

    registrar_incidencia("La VPN da error de certificado", "Red", "Usuario", "Alta")

    cerrar_ticket("TCK-0001", SOLUCION)
 
    resueltas = _resueltas_por_id("TCK-0001")

    assert len(resueltas) == 1

    assert resueltas[0]["origen"] == "ticket"

    assert resueltas[0]["categoria"] == "Red"

    assert resueltas[0]["solucion"] == SOLUCION
 
 
def test_el_buscador_encuentra_el_ticket_cerrado():

    """El ciclo completo: un ticket cerrado se propone como solución en incidencias parecidas."""

    registrar_incidencia("El plóter zxq de arquitectura no imprime planos", "Hardware", "Usuario", "Media")

    cerrar_ticket("TCK-0001", "Se cambió el cabezal del plóter zxq y se recalibró.")
 
    resultado = buscar_incidencias_similares("plóter zxq sin imprimir", "Hardware")

    assert resultado["incidencias"][0]["id"] == "TCK-0001"

    assert "cabezal" in resultado["incidencias"][0]["solucion"]
 
 
def test_cerrar_acepta_minusculas_y_espacios():

    registrar_incidencia("Outlook no abre", "Software", "Usuario", "Media")

    assert cerrar_ticket("  tck-0001 ", SOLUCION)["estado"] == "cerrada"
 
 
def test_cerrar_ticket_inexistente_devuelve_error():

    resultado = cerrar_ticket("TCK-0099", SOLUCION)

    assert "error" in resultado
 
 
def test_cerrar_ticket_ya_cerrado_devuelve_error_y_no_duplica():

    registrar_incidencia("Outlook no abre", "Software", "Usuario", "Media")

    cerrar_ticket("TCK-0001", SOLUCION)

    resultado = cerrar_ticket("TCK-0001", "Otra solución distinta para el mismo ticket.")
 
    assert "error" in resultado

    assert len(_resueltas_por_id("TCK-0001")) == 1

    assert _tickets_en_bd()[0]["solucion"] == SOLUCION
 
 
@pytest.mark.parametrize("solucion", ["", "   ", "Hecho."])

def test_cerrar_sin_solucion_no_cambia_nada(solucion):

    registrar_incidencia("Outlook no abre", "Software", "Usuario", "Media")

    resultado = cerrar_ticket("TCK-0001", solucion)
 
    assert "error" in resultado

    assert _tickets_en_bd()[0]["estado"] == "abierta"

    assert _resueltas_por_id("TCK-0001") == []
 
 
@pytest.mark.parametrize("id_ticket", ["", "1", "TCK-1", "INC-001", "TCK-00011"])

def test_cerrar_con_id_invalido_devuelve_error(id_ticket):

    assert "error" in cerrar_ticket(id_ticket, SOLUCION)
 
 
def test_consultar_por_estado():

    registrar_incidencia("Caso 1", "Red", "Usuario", "Baja")

    registrar_incidencia("Caso 2", "Red", "Usuario", "Baja")

    cerrar_ticket("TCK-0001", SOLUCION)
 
    assert consultar_tickets()["total"] == 1  # por defecto, solo abiertas

    assert consultar_tickets(estado="abierta")["tickets_recientes"][0]["id"] == "TCK-0002"

    assert consultar_tickets(estado="cerrada")["tickets_recientes"][0]["id"] == "TCK-0001"

    assert consultar_tickets(estado="todas")["total"] == 2
 
 
# -------------------------------------------------------------------------

# Ver un ticket

# -------------------------------------------------------------------------
 
def test_ver_ticket_abierto():

    registrar_incidencia("La VPN da error de certificado", "Red", "Usuario", "Alta")

    ticket = ver_ticket("TCK-0001")
 
    assert ticket["id"] == "TCK-0001"

    assert ticket["descripcion"] == "La VPN da error de certificado"

    assert ticket["categoria"] == "Red"

    assert ticket["prioridad"] == "P2"

    assert ticket["estado"] == "abierta"

    assert "solucion" not in ticket
 
 
def test_ver_ticket_cerrado_incluye_solucion():

    registrar_incidencia("La VPN da error de certificado", "Red", "Usuario", "Alta")

    cerrar_ticket("TCK-0001", SOLUCION)

    ticket = ver_ticket("tck-0001")
 
    assert ticket["estado"] == "cerrada"

    assert ticket["solucion"] == SOLUCION

    assert ticket["fecha_cierre"] is not None
 
 
def test_ver_ticket_inexistente_o_invalido():

    assert "error" in ver_ticket("TCK-0099")

    assert "error" in ver_ticket("INC-001")
 