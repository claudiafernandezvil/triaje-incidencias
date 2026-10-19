"""Módulo FinOps para el control de costes y consumo de tokens en los agentes."""

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import litellm
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# Precios de reserva (USD por millón de tokens) si LiteLLM no conoce el modelo
PRECIOS_POR_MILLON = {
    "gpt-5.4-nano": {"entrada": 0.20, "salida": 1.25},
    "gpt-5.4-mini": {"entrada": 0.75, "salida": 4.50},
}

DEFAULT_MAX_TOKENS_INCIDENCIA = 20000
DEFAULT_PRESUPUESTO_TOTAL_USD = 5.0
DEFAULT_CSV_PATH = Path("logs/costes.csv")


def _obtener_ruta_csv() -> Path:
    """Devuelve la ruta al archivo CSV de registro de costes."""
    ruta = os.getenv("RUTA_LOGS_COSTES")
    return Path(ruta) if ruta else DEFAULT_CSV_PATH


def calcular_coste(modelo: str, tokens_entrada: int, tokens_salida: int) -> float:
    """Calcula el coste de una llamada al LLM en USD.

    Primero intenta utilizar litellm.cost_per_token. Si el modelo no está en
    LiteLLM o lanza una excepción, consulta el diccionario local PRECIOS_POR_MILLON.
    """
    modelo_limpio = (modelo or "").strip()
    if not modelo_limpio:
        return 0.0

    # 1. Intentar cálculo nativo de LiteLLM
    try:
        costes = litellm.cost_per_token(
            model=modelo_limpio,
            prompt_tokens=tokens_entrada,
            completion_tokens=tokens_salida,
        )
        if costes is not None:
            prompt_cost, completion_cost = costes
            if prompt_cost is not None and completion_cost is not None:
                # Comprobar que no es 0.0 por modelo desconocido en el diccionario interno
                coste_total = float(prompt_cost + completion_cost)
                if coste_total > 0.0 or modelo_limpio in getattr(litellm, "model_cost", {}):
                    return coste_total
    except Exception:
        pass

    # 2. Fallback a diccionario de precios local
    modelo_normalizado = modelo_limpio.lower()
    if "/" in modelo_normalizado:
        modelo_normalizado = modelo_normalizado.split("/", 1)[1]

    if modelo_normalizado in PRECIOS_POR_MILLON:
        precios = PRECIOS_POR_MILLON[modelo_normalizado]
        coste_entrada = (tokens_entrada * precios["entrada"]) / 1_000_000.0
        coste_salida = (tokens_salida * precios["salida"]) / 1_000_000.0
        return coste_entrada + coste_salida

    return 0.0


def registrar_coste_csv(
    fecha: str,
    id_sesion: str,
    nombre_agente: str,
    modelo: str,
    tokens_entrada: int,
    tokens_salida: int,
    coste_usd: float,
    ruta_csv: Path | None = None,
) -> None:
    """Registra una llamada en el archivo CSV de costes."""
    destino = ruta_csv or _obtener_ruta_csv()
    destino.parent.mkdir(parents=True, exist_ok=True)

    archivo_nuevo = not destino.exists() or destino.stat().st_size == 0
    with open(destino, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if archivo_nuevo:
            writer.writerow([
                "fecha",
                "id_sesion",
                "nombre_agente",
                "modelo",
                "tokens_entrada",
                "tokens_salida",
                "coste_usd",
            ])
        writer.writerow([
            fecha,
            id_sesion,
            nombre_agente,
            modelo,
            tokens_entrada,
            tokens_salida,
            f"{coste_usd:.8f}",
        ])


def obtener_gasto_acumulado_usd(ruta_csv: Path | None = None) -> float:
    """Calcula el gasto total acumulado en USD a partir del CSV de costes."""
    destino = ruta_csv or _obtener_ruta_csv()
    if not destino.exists():
        return 0.0

    total = 0.0
    try:
        with open(destino, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                coste_str = row.get("coste_usd")
                if coste_str:
                    try:
                        total += float(coste_str)
                    except ValueError:
                        continue
    except Exception:
        return 0.0

    return total


def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """Comprueba los límites de presupuesto antes de ejecutar una llamada al modelo.

    Verifica el presupuesto total acumulado del proyecto (PRESUPUESTO_TOTAL_USD)
    y el límite de tokens acumulados en la sesión (MAX_TOKENS_INCIDENCIA).
    """
    # 1. Comprobar presupuesto global del proyecto
    try:
        presupuesto_total = float(
            os.getenv("PRESUPUESTO_TOTAL_USD", str(DEFAULT_PRESUPUESTO_TOTAL_USD))
        )
    except ValueError:
        presupuesto_total = DEFAULT_PRESUPUESTO_TOTAL_USD

    gasto_acumulado = obtener_gasto_acumulado_usd()
    if gasto_acumulado >= presupuesto_total:
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="Presupuesto total del proyecto agotado. No se pueden realizar más llamadas."
                    )
                ],
            )
        )

    # 2. Comprobar límite de tokens en la sesión actual
    try:
        max_tokens_incidencia = int(
            os.getenv("MAX_TOKENS_INCIDENCIA", str(DEFAULT_MAX_TOKENS_INCIDENCIA))
        )
    except ValueError:
        max_tokens_incidencia = DEFAULT_MAX_TOKENS_INCIDENCIA

    tokens_acumulados = 0
    if hasattr(callback_context, "state") and callback_context.state is not None:
        tokens_acumulados = callback_context.state.get("total_tokens", 0)

    if tokens_acumulados >= max_tokens_incidencia:
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        text="Presupuesto de tokens por incidencia superado. Operación cancelada."
                    )
                ],
            )
        )

    return None


def after_model_callback(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Lee el consumo de tokens, calcula el coste, registra en CSV y acumula en sesión."""
    if not llm_response:
        return llm_response

    # Ignorar respuestas parciales de streaming
    if getattr(llm_response, "partial", False):
        return llm_response

    # Ignorar respuestas sin metadatos de uso
    usage_metadata = getattr(llm_response, "usage_metadata", None)
    if not usage_metadata:
        return llm_response

    prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
    candidates_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
    total_tokens = getattr(usage_metadata, "total_token_count", None)
    if total_tokens is None:
        total_tokens = prompt_tokens + candidates_tokens

    # Ignorar respuestas con 0 tokens
    if total_tokens == 0:
        return llm_response

    # Obtener nombre del modelo
    modelo = getattr(llm_response, "model_version", None)
    if not modelo:
        agent_obj = getattr(
            getattr(callback_context, "_invocation_context", None), "agent", None
        )
        agent_model = getattr(agent_obj, "model", None)
        modelo = getattr(agent_model, "model", str(agent_model))
    if not modelo:
        modelo = "desconocido"

    coste = calcular_coste(modelo, prompt_tokens, candidates_tokens)

    # Obtener metadatos de sesión y agente
    session_obj = getattr(callback_context, "session", None)
    id_sesion = getattr(session_obj, "id", "sesion_desconocida")
    nombre_agente = getattr(callback_context, "agent_name", "agente_desconocido")
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Registrar en logs/costes.csv
    try:
        registrar_coste_csv(
            fecha=fecha,
            id_sesion=id_sesion,
            nombre_agente=nombre_agente,
            modelo=modelo,
            tokens_entrada=prompt_tokens,
            tokens_salida=candidates_tokens,
            coste_usd=coste,
        )
    except Exception:
        pass

    # Acumular en callback_context.state
    if hasattr(callback_context, "state") and callback_context.state is not None:
        tokens_previos = callback_context.state.get("total_tokens", 0)
        callback_context.state["total_tokens"] = tokens_previos + (
            prompt_tokens + candidates_tokens
        )

        coste_previo = callback_context.state.get("total_coste_usd", 0.0)
        callback_context.state["total_coste_usd"] = coste_previo + coste

    return llm_response
