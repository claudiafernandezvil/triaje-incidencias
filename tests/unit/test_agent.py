import importlib
import os
from unittest.mock import patch

import pytest


def test_missing_openai_api_key_raises_error():
    """Verifica que el programa falla con un mensaje claro si OPENAI_API_KEY no existe."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ):
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ["MODELO_SENCILLO"] = "gpt-4o-mini"
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                import app.agent
                importlib.reload(app.agent)


def test_missing_modelo_sencillo_raises_error():
    """Verifica que el programa falla si MODELO_SENCILLO no existe."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ):
            os.environ["OPENAI_API_KEY"] = "dummy_test_key"
            os.environ.pop("MODELO_SENCILLO", None)
            with pytest.raises(ValueError, match="MODELO_SENCILLO"):
                import app.agent
                importlib.reload(app.agent)


def test_agent_initialization_with_litellm():
    """Verifica que el agente se inicializa con LiteLLM y las 4 categorías."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "dummy_test_key", "MODELO_SENCILLO": "gpt-4o-mini"},
        ):
            import app.agent
            importlib.reload(app.agent)

            agent = app.agent.root_agent
            assert agent is not None
            assert agent.name == "root_agent"

            from google.adk.models.lite_llm import LiteLlm
            assert isinstance(agent.model, LiteLlm)
            assert agent.model.model == "openai/gpt-4o-mini"

            # Verificar que la instrucción contiene las 4 categorías
            instruction = agent.instruction
            assert "Red" in instruction
            assert "Software" in instruction
            assert "Hardware" in instruction
            assert "Accesos" in instruction
