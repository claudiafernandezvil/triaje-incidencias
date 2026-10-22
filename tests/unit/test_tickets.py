"""Tests de las herramientas de tickets (no llaman a OpenAI).
 
Cada test usa una base de datos temporal (ver conftest.py).
"""
 
import pytest
 
from app.db import conectar
from app.tickets import consultar_tickets, registrar_incidencia
 
 
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