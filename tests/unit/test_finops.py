"""Pruebas unitarias para el módulo FinOps (app/finops.py) y script de informes."""

import csv
from unittest.mock import MagicMock, patch

import pytest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app.finops import (
    after_model_callback,
    before_model_callback,
    calcular_coste,
    obtener_gasto_acumulado_usd,
    registrar_coste_csv,
)
from scripts.informe_costes import generar_informe

# -----------------------------------------------------------------------------
# 1. Tests para calcular_coste
# -----------------------------------------------------------------------------

def test_calcular_coste_litellm_exitoso():
    """Verifica que si LiteLLM devuelve coste, se utiliza ese valor directamente."""
    with patch("litellm.cost_per_token", return_value=(0.0015, 0.0025)):
        coste = calcular_coste("gpt-4o", tokens_entrada=1000, tokens_salida=500)
        assert coste == pytest.approx(0.0040)


def test_calcular_coste_fallback_nano():
    """Verifica el cálculo de coste con el diccionario de reserva para gpt-5.4-nano."""
    # gpt-5.4-nano: 0.20 entrada / 1M, 1.25 salida / 1M
    with patch("litellm.cost_per_token", side_effect=Exception("Modelo no soportado")):
        # 1.000.000 tokens de entrada y 1.000.000 de salida
        coste_1m = calcular_coste("gpt-5.4-nano", 1_000_000, 1_000_000)
        assert coste_1m == pytest.approx(0.20 + 1.25)

        # Caso proporcional con prefijo openai/
        coste_frac = calcular_coste("openai/gpt-5.4-nano", 10_000, 2_000)
        # 10_000 * 0.20 / 1e6 = 0.002; 2_000 * 1.25 / 1e6 = 0.0025
        assert coste_frac == pytest.approx(0.0045)


def test_calcular_coste_fallback_mini():
    """Verifica el cálculo de coste con el diccionario de reserva para gpt-5.4-mini."""
    # gpt-5.4-mini: 0.75 entrada / 1M, 4.50 salida / 1M
    with patch("litellm.cost_per_token", side_effect=Exception("Modelo no soportado")):
        coste_1m = calcular_coste("gpt-5.4-mini", 1_000_000, 1_000_000)
        assert coste_1m == pytest.approx(0.75 + 4.50)

        coste_frac = calcular_coste("openai/gpt-5.4-mini", 10_000, 1_000)
        # 10_000 * 0.75 / 1e6 = 0.0075; 1_000 * 4.50 / 1e6 = 0.0045
        assert coste_frac == pytest.approx(0.0120)


def test_calcular_coste_modelo_desconocido():
    """Verifica que un modelo desconocido para LiteLLM y sin fallback devuelve 0.0."""
    with patch("litellm.cost_per_token", side_effect=Exception("Desconocido")):
        coste = calcular_coste("modelo-inventado-xyz", 1000, 1000)
        assert coste == 0.0


def test_calcular_coste_modelo_vacio():
    """Verifica que un modelo vacío o None devuelve 0.0."""
    assert calcular_coste("", 100, 100) == 0.0
    assert calcular_coste(None, 100, 100) == 0.0  # type: ignore


# -----------------------------------------------------------------------------
# 2. Tests para registro en CSV y acumulación de estado
# -----------------------------------------------------------------------------

def test_registrar_coste_csv(tmp_path):
    """Verifica que registrar_coste_csv crea el fichero con cabecera y añade filas."""
    csv_file = tmp_path / "logs" / "test_costes.csv"

    registrar_coste_csv(
        fecha="2026-10-19 10:00:00",
        id_sesion="ses-001",
        nombre_agente="clasificador",
        modelo="gpt-5.4-nano",
        tokens_entrada=100,
        tokens_salida=50,
        coste_usd=0.0001,
        ruta_csv=csv_file,
    )

    assert csv_file.exists()
    with open(csv_file, encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 2
        assert reader[0] == [
            "fecha",
            "id_sesion",
            "nombre_agente",
            "modelo",
            "tokens_entrada",
            "tokens_salida",
            "coste_usd",
        ]
        assert reader[1][1] == "ses-001"
        assert reader[1][2] == "clasificador"
        assert reader[1][3] == "gpt-5.4-nano"


def test_obtener_gasto_acumulado_usd(tmp_path):
    """Verifica que se sume adecuadamente el coste total del CSV."""
    csv_file = tmp_path / "costes.csv"
    assert obtener_gasto_acumulado_usd(csv_file) == 0.0

    registrar_coste_csv("2026-10-19 10:00:00", "s1", "a1", "m", 10, 10, 1.25, ruta_csv=csv_file)
    registrar_coste_csv("2026-10-19 10:01:00", "s1", "a2", "m", 10, 10, 0.75, ruta_csv=csv_file)

    total = obtener_gasto_acumulado_usd(csv_file)
    assert total == pytest.approx(2.0)


def test_after_model_callback_actualiza_estado_y_csv(tmp_path, monkeypatch):
    """Verifica que after_model_callback calcula coste, escribe CSV y actualiza callback_context.state."""
    csv_file = tmp_path / "costes.csv"
    monkeypatch.setenv("RUTA_LOGS_COSTES", str(csv_file))

    # Mock de CallbackContext
    ctx = MagicMock()
    ctx.session.id = "ses-test-99"
    ctx.agent_name = "clasificador"
    ctx.state = {}

    # Mock de LlmResponse con usage_metadata
    response = LlmResponse(
        model_version="gpt-5.4-nano",
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=1000,
            candidates_token_count=500,
            total_token_count=1500,
        ),
    )

    with patch("litellm.cost_per_token", side_effect=Exception("No en litellm")):
        ret_val = after_model_callback(ctx, response)

        assert ret_val is response
        # 1000 + 500 = 1500 tokens
        assert ctx.state["total_tokens"] == 1500

        # Coste gpt-5.4-nano: 1000 * 0.20/1e6 + 500 * 1.25/1e6 = 0.0002 + 0.000625 = 0.000825
        assert ctx.state["total_coste_usd"] == pytest.approx(0.000825)

        # Segunda llamada acumula
        after_model_callback(ctx, response)
        assert ctx.state["total_tokens"] == 3000
        assert ctx.state["total_coste_usd"] == pytest.approx(0.00165)

        # CSV contiene 2 entradas más cabecera
        total_acumulado = obtener_gasto_acumulado_usd(csv_file)
        assert total_acumulado == pytest.approx(0.00165)


# -----------------------------------------------------------------------------
# 3. Tests para corte por presupuesto (before_model_callback)
# -----------------------------------------------------------------------------

def test_before_model_callback_permite_llamada_bajo_limite(tmp_path, monkeypatch):
    """Verifica que devuelve None si el gasto y los tokens están dentro de los límites."""
    csv_file = tmp_path / "costes.csv"
    monkeypatch.setenv("RUTA_LOGS_COSTES", str(csv_file))
    monkeypatch.setenv("MAX_TOKENS_INCIDENCIA", "20000")
    monkeypatch.setenv("PRESUPUESTO_TOTAL_USD", "5.0")

    ctx = MagicMock()
    ctx.state = {"total_tokens": 1500}
    req = MagicMock()

    resultado = before_model_callback(ctx, req)
    assert resultado is None


def test_before_model_callback_corte_por_tokens_incidencia(tmp_path, monkeypatch):
    """Verifica que corta y devuelve LlmResponse cuando la sesión supera MAX_TOKENS_INCIDENCIA."""
    csv_file = tmp_path / "costes.csv"
    monkeypatch.setenv("RUTA_LOGS_COSTES", str(csv_file))
    monkeypatch.setenv("MAX_TOKENS_INCIDENCIA", "20000")
    monkeypatch.setenv("PRESUPUESTO_TOTAL_USD", "100.0")

    ctx = MagicMock()
    ctx.state = {"total_tokens": 20000}
    req = MagicMock()

    resultado = before_model_callback(ctx, req)
    assert isinstance(resultado, LlmResponse)
    assert resultado.content is not None
    assert "Presupuesto de tokens por incidencia superado" in resultado.content.parts[0].text


def test_before_model_callback_corte_por_presupuesto_total(tmp_path, monkeypatch):
    """Verifica que corta cuando el gasto registrado en CSV alcanza o supera PRESUPUESTO_TOTAL_USD."""
    csv_file = tmp_path / "costes.csv"
    monkeypatch.setenv("RUTA_LOGS_COSTES", str(csv_file))
    monkeypatch.setenv("MAX_TOKENS_INCIDENCIA", "20000")
    monkeypatch.setenv("PRESUPUESTO_TOTAL_USD", "5.0")

    # Registrar gasto previo de 5.5 USD en el CSV
    registrar_coste_csv("2026-10-19 10:00:00", "s1", "a1", "m", 100, 100, 5.5, ruta_csv=csv_file)

    ctx = MagicMock()
    ctx.state = {"total_tokens": 100}  # Bajo límite de tokens
    req = MagicMock()

    resultado = before_model_callback(ctx, req)
    assert isinstance(resultado, LlmResponse)
    assert resultado.content is not None
    assert "Presupuesto total del proyecto agotado" in resultado.content.parts[0].text


# -----------------------------------------------------------------------------
# 4. Tests para scripts/informe_costes.py
# -----------------------------------------------------------------------------

def test_informe_costes_csv_inexistente(tmp_path, capsys):
    """Verifica la ejecución limpia del informe cuando no hay CSV."""
    archivo_vacio = tmp_path / "no_existe.csv"
    generar_informe(archivo_vacio)
    salida = capsys.readouterr().out
    assert "INFORME DE CONTROL DE COSTES" in salida
    assert "No se encontraron registros de costes" in salida


def test_informe_costes_con_datos(tmp_path, capsys, monkeypatch):
    """Verifica que el informe calcula y muestra correctamente los agregados y proyecciones."""
    csv_file = tmp_path / "costes.csv"
    monkeypatch.setenv("PRESUPUESTO_TOTAL_USD", "10.0")

    registrar_coste_csv("2026-10-19 10:00:00", "inc-1", "clasificador", "gpt-5.4-nano", 100, 50, 0.05, ruta_csv=csv_file)
    registrar_coste_csv("2026-10-19 10:01:00", "inc-1", "redactor", "gpt-5.4-mini", 200, 100, 0.15, ruta_csv=csv_file)
    registrar_coste_csv("2026-10-19 10:05:00", "inc-2", "clasificador", "gpt-5.4-nano", 100, 50, 0.05, ruta_csv=csv_file)

    generar_informe(csv_file)
    salida = capsys.readouterr().out

    assert "INFORME DE CONTROL DE COSTES" in salida
    assert "$0.2500 USD" in salida  # Gasto total (0.05 + 0.15 + 0.05)
    assert "redactor" in salida  # Agente más caro
    assert "Total incidencias procesadas: 2" in salida
    assert "Proyección para 1.000 incidencias/mes" in salida
