"""Tests de la base de datos SQLite (app/db.py). No llaman a OpenAI.
 
Cada test usa una base de datos temporal (ver conftest.py).
"""
 
from app.db import conectar
 
 
def test_crea_las_tablas(base_de_datos_temporal):
    with conectar() as conexion:
        tablas = {
            fila["name"]
            for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert {"incidencias_resueltas", "tickets"} <= tablas
    assert base_de_datos_temporal.exists()
 
 
def test_carga_el_historial_inicial_una_sola_vez():
    with conectar() as conexion:
        total = conexion.execute("SELECT COUNT(*) FROM incidencias_resueltas").fetchone()[0]
    assert total == 40
 
    # Al volver a conectar no se duplican los datos
    with conectar() as conexion:
        total_otra_vez = conexion.execute("SELECT COUNT(*) FROM incidencias_resueltas").fetchone()[0]
    assert total_otra_vez == 40
 
 
def test_historial_inicial_marcado_como_historial():
    with conectar() as conexion:
        origenes = {f["origen"] for f in conexion.execute("SELECT origen FROM incidencias_resueltas")}
    assert origenes == {"historial"}
 
 
def test_un_error_deshace_los_cambios():
    try:
        with conectar() as conexion:
            conexion.execute(
                "INSERT INTO tickets (id, fecha, descripcion, categoria, impacto, urgencia, prioridad) "
                "VALUES ('TCK-9999', 'hoy', 'prueba', 'Red', 'Usuario', 'Alta', 'P2')"
            )
            raise RuntimeError("fallo simulado")
    except RuntimeError:
        pass
 
    with conectar() as conexion:
        total = conexion.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    assert total == 0