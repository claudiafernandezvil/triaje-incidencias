"""Pruebas unitarias para las herramientas en app/tools.py."""
 
import sqlite3
from unittest.mock import patch
 
import pytest
 
from app.tools import buscar_incidencias_similares, calcular_prioridad
 
 
# -------------------------------------------------------------------------
# Tests para calcular_prioridad
# -------------------------------------------------------------------------
 
@pytest.mark.parametrize(
    ("impacto", "urgencia", "prioridad_esperada"),
    [
        ("Departamento", "Alta", "P1"),
        ("Departamento", "Media", "P2"),
        ("Departamento", "Baja", "P3"),
        ("Usuario", "Alta", "P2"),
        ("Usuario", "Media", "P3"),
        ("Usuario", "Baja", "P4"),
    ],
)
def test_calcular_prioridad_matriz_casos_validos(impacto, urgencia, prioridad_esperada):
    """Verifica los 6 casos exactos de la matriz fija de prioridad."""
    resultado = calcular_prioridad(impacto, urgencia)
 
    assert "error" not in resultado
    assert resultado["prioridad"] == prioridad_esperada
    assert resultado["impacto"] == impacto
    assert resultado["urgencia"] == urgencia
 
 
@pytest.mark.parametrize(
    ("impacto", "urgencia"),
    [
        ("Empresa", "Alta"),          # Impacto no reconocido
        ("Departamento", "Critica"),  # Urgencia no reconocida
        ("Invalido", "Invalido"),     # Ambos no reconocidos
        ("", "Alta"),                 # Impacto vacío
        ("Usuario", ""),              # Urgencia vacía
        ("123", "Baja"),              # Valor numérico como texto
    ],
)
def test_calcular_prioridad_valores_invalidos(impacto, urgencia):
    """Verifica que valores inválidos devuelven un error descriptivo sin lanzar excepción."""
    resultado = calcular_prioridad(impacto, urgencia)
 
    assert isinstance(resultado, dict)
    assert "error" in resultado
    assert "prioridad" not in resultado
 
 
def test_calcular_prioridad_tipos_invalidos():
    """Verifica que el paso de tipos incorrectos (ej. None o enteros) no lance excepción."""
    resultado = calcular_prioridad(None, 123)  # type: ignore
 
    assert isinstance(resultado, dict)
    assert "error" in resultado
    assert "prioridad" not in resultado
 
 
def test_calcular_prioridad_espacios_y_capitalizacion():
    """Verifica que tolera espacios en blanco y variaciones en mayúsculas/minúsculas."""
    resultado = calcular_prioridad("  departamento  ", "  ALTA  ")
 
    assert "error" not in resultado
    assert resultado["prioridad"] == "P1"
 
 
# -------------------------------------------------------------------------
# Tests para buscar_incidencias_similares
# -------------------------------------------------------------------------
 
def test_buscar_incidencias_similares_filtro_categoria():
    """Verifica que solo se recuperan incidencias de la categoría solicitada."""
    # El historial inicial contiene incidencias de Red como INC-001 (VPN), INC-002 (Wi-Fi), etc.
    resultado = buscar_incidencias_similares("problemas con la conexion VPN", categoria="Red")
 
    assert "error" not in resultado
    incidencias = resultado["incidencias"]
    assert len(incidencias) > 0
 
    # Comprobar que los IDs devueltos pertenecen efectivamente al bloque de Red (INC-001 a INC-010)
    for inc in incidencias:
        assert inc["id"].startswith("INC-00")
        assert "descripcion" in inc
        assert "solucion" in inc
 
 
def test_buscar_incidencias_similares_orden_palabras():
    """Verifica que los resultados se ordenan de mayor a menor número de palabras coincidentes."""
    # Consulta orientada a Outlook y perfil en categoría Software
    # INC-011: 'Outlook no se abre, se queda cargando el perfil'
    resultado = buscar_incidencias_similares(
        descripcion="Outlook no abre y falla el perfil de usuario",
        categoria="Software",
        max_resultados=3,
    )
 
    assert "error" not in resultado
    incidencias = resultado["incidencias"]
    assert len(incidencias) > 0
    # La más coincidente debe ser INC-011
    assert incidencias[0]["id"] == "INC-011"
 
 
def test_buscar_incidencias_similares_max_resultados():
    """Verifica que se respeta el límite max_resultados."""
    resultado = buscar_incidencias_similares(
        descripcion="no funciona",
        categoria="Red",
        max_resultados=2,
    )
 
    assert "error" not in resultado
    assert len(resultado["incidencias"]) <= 2
 
 
def test_buscar_incidencias_similares_sin_coincidencias():
    """Verifica que una búsqueda sin coincidencias de palabras devuelve lista vacía sin error."""
    resultado = buscar_incidencias_similares(
        descripcion="palabraquejamasexistiraentrelosdatos 999xyz",
        categoria="Red",
    )
 
    assert "error" not in resultado
    assert resultado["incidencias"] == []
    assert resultado["total"] == 0
 
 
def test_buscar_incidencias_similares_error_base_de_datos():
    """Verifica el comportamiento seguro si la base de datos no está disponible."""
    with patch("app.tools.conectar", side_effect=sqlite3.OperationalError("base de datos no disponible")):
        resultado = buscar_incidencias_similares("vpn", "Red")
 
        assert "error" in resultado
        assert resultado["incidencias"] == []
 
 
def test_buscar_incluye_incidencias_anadidas_al_historial():
    """Verifica que la búsqueda usa la base de datos: una incidencia nueva en el historial aparece."""
    from app.db import conectar
 
    with conectar() as conexion:
        conexion.execute(
            "INSERT INTO incidencias_resueltas (id, descripcion, categoria, solucion, origen) "
            "VALUES ('TCK-0001', 'El escáner zxq del almacén no enciende', 'Hardware', "
            "'Sustituir la fuente del escáner zxq', 'ticket')"
        )
 
    resultado = buscar_incidencias_similares("escáner zxq averiado", "Hardware")
    assert resultado["incidencias"][0]["id"] == "TCK-0001"