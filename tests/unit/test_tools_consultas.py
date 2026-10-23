"""Tests de la herramienta estadisticas_historial (no llaman a OpenAI)."""
 
from app.tools_consultas import CATEGORIAS_VALIDAS, estadisticas_historial
 
 
def test_total_sin_filtro():
    resultado = estadisticas_historial()
    assert resultado["filtro_categoria"] == "todas"
    assert resultado["total"] == 40
    assert set(resultado["por_categoria"]) == set(CATEGORIAS_VALIDAS)
 
 
def test_reparto_por_categoria_suma_el_total():
    resultado = estadisticas_historial()
    assert sum(resultado["por_categoria"].values()) == resultado["total"]
 
 
def test_filtro_por_categoria():
    resultado = estadisticas_historial("Red")
    assert resultado["filtro_categoria"] == "Red"
    assert resultado["total"] == 10
    assert resultado["por_categoria"] == {"Red": 10}
 
 
def test_filtro_ignora_mayusculas_y_espacios():
    resultado = estadisticas_historial("  accesos ")
    assert resultado["filtro_categoria"] == "Accesos"
    assert resultado["total"] == 10
 
 
def test_categoria_invalida_devuelve_error():
    resultado = estadisticas_historial("Impresoras")
    assert "error" in resultado
 
 
def test_prioridades_suman_el_total_y_son_validas():
    resultado = estadisticas_historial()
    assert sum(resultado["por_prioridad"].values()) == resultado["total"]
    assert set(resultado["por_prioridad"]) <= {"P1", "P2", "P3", "P4"}
 
 
def test_ejemplos_limitados_y_con_campos():
    resultado = estadisticas_historial("Hardware")
    assert 0 < len(resultado["ejemplos"]) <= 5
    for ejemplo in resultado["ejemplos"]:
        assert set(ejemplo) == {"id", "descripcion"}
 
 
def test_reparto_por_origen():
    resultado = estadisticas_historial()
    assert resultado["por_origen"] == {"historial": 40}