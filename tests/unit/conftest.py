"""Configuración común de los tests unitarios."""
 
import pytest
 
 
@pytest.fixture(autouse=True)
def base_de_datos_temporal(tmp_path, monkeypatch):
    """Cada test usa su propia base de datos SQLite, vacía y temporal.
 
    Se crea sola al primer uso y carga el historial inicial del CSV, así que
    los tests nunca tocan la base de datos real (data/soporte.db).
    """
    ruta = tmp_path / "soporte_test.db"
    monkeypatch.setenv("RUTA_BD", str(ruta))
    return ruta