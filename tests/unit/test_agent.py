"""Pruebas unitarias para app/agent.py."""
 
import importlib
import os
from unittest.mock import patch
 
import pytest
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
 
from app.tools import buscar_incidencias_similares, calcular_prioridad
from app.tools_consultas import estadisticas_historial
 
 
def test_missing_openai_api_key_raises_error():
    """Verifica que el programa falla con un mensaje claro si OPENAI_API_KEY no existe."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ):
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ["MODELO_SENCILLO"] = "gpt-4o-mini"
            os.environ["MODELO_REDACCION"] = "gpt-4o"
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                import app.agent
 
                importlib.reload(app.agent)
 
 
def test_missing_modelo_sencillo_raises_error():
    """Verifica que el programa falla si MODELO_SENCILLO no existe."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ):
            os.environ["OPENAI_API_KEY"] = "dummy_test_key"
            os.environ.pop("MODELO_SENCILLO", None)
            os.environ["MODELO_REDACCION"] = "gpt-4o"
            with pytest.raises(ValueError, match="MODELO_SENCILLO"):
                import app.agent
 
                importlib.reload(app.agent)
 
 
def test_missing_modelo_redaccion_raises_error():
    """Verifica que el programa falla si MODELO_REDACCION no existe."""
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ):
            os.environ["OPENAI_API_KEY"] = "dummy_test_key"
            os.environ["MODELO_SENCILLO"] = "gpt-4o-mini"
            os.environ.pop("MODELO_REDACCION", None)
            with pytest.raises(ValueError, match="MODELO_REDACCION"):
                import app.agent
 
                importlib.reload(app.agent)
 
 
def test_estructura_coordinador_triaje_y_consultas():
    """Verifica la jerarquía: coordinador (raíz) -> triaje (SequentialAgent con 3 subagentes) y consultas."""
    env_vars = {
        "OPENAI_API_KEY": "dummy_test_key",
        "MODELO_SENCILLO": "gpt-4o-mini",
        "MODELO_REDACCION": "gpt-4o",
    }
    with patch("dotenv.load_dotenv"):
        with patch.dict(os.environ, env_vars):
            import app.agent
 
            importlib.reload(app.agent)
 
            root = app.agent.root_agent
 
            # 0. Coordinador (agente raíz)
            assert isinstance(root, LlmAgent), "root_agent debe ser un LlmAgent (coordinador)"
            assert root.name == "coordinador"
            assert isinstance(root.model, LiteLlm)
            assert root.model.model == "openai/gpt-4o-mini"
            assert [ag.name for ag in root.sub_agents] == ["triaje", "consultas"]
            assert "triaje" in root.instruction
            assert "consultas" in root.instruction
            assert root.before_model_callback == app.agent.before_model_callback
            assert root.after_model_callback == app.agent.after_model_callback
            assert root.generate_content_config.temperature == 0.0
 
            # Pipeline de triaje
            triaje = root.sub_agents[0]
            assert isinstance(triaje, SequentialAgent), "triaje debe ser un SequentialAgent"
            assert triaje.description, "triaje necesita descripción para el enrutado"
 
            # Verificar orden y cantidad de subagentes del triaje
            sub_agents = triaje.sub_agents
            assert len(sub_agents) == 3, (
                "triaje debe tener exactamente 3 subagentes"
            )
            nombres = [ag.name for ag in sub_agents]
            assert nombres == ["clasificador", "buscador", "redactor"], (
                f"El orden de los subagentes debe ser ['clasificador', 'buscador', 'redactor'], recibido: {nombres}"
            )
 
            # 1. Subagente clasificador
            clasificador = sub_agents[0]
            assert isinstance(clasificador, LlmAgent)
            assert isinstance(clasificador.model, LiteLlm)
            assert clasificador.model.model == "openai/gpt-4o-mini"
            assert clasificador.output_key == "clasificacion"
            assert calcular_prioridad in clasificador.tools
            assert "Red" in clasificador.instruction
            assert "Software" in clasificador.instruction
            assert "Hardware" in clasificador.instruction
            assert "Accesos" in clasificador.instruction
            assert "calcular_prioridad" in clasificador.instruction
            assert "requiere más información" in clasificador.instruction
            assert (
                "si no es ninguna de las anteriores" in clasificador.instruction.lower()
            )
            assert "Departamento" in clasificador.instruction
            assert "Usuario" in clasificador.instruction
            assert clasificador.before_model_callback == app.agent.before_model_callback
            assert clasificador.after_model_callback == app.agent.after_model_callback
            assert clasificador.generate_content_config.max_output_tokens == 500
            assert clasificador.generate_content_config.temperature == 0.0
 
            # 2. Subagente buscador
            buscador = sub_agents[1]
            assert isinstance(buscador, LlmAgent)
            assert isinstance(buscador.model, LiteLlm)
            assert buscador.model.model == "openai/gpt-4o-mini"
            assert buscador.output_key == "similares"
            assert buscar_incidencias_similares in buscador.tools
            assert "{clasificacion}" in buscador.instruction
            assert "buscar_incidencias_similares" in buscador.instruction
            assert "requiere más información" in buscador.instruction
            assert buscador.before_model_callback == app.agent.before_model_callback
            assert buscador.after_model_callback == app.agent.after_model_callback
            assert buscador.generate_content_config.max_output_tokens == 500
 
            # 3. Subagente redactor
            redactor = sub_agents[2]
            assert isinstance(redactor, LlmAgent)
            assert isinstance(redactor.model, LiteLlm)
            assert redactor.model.model == "openai/gpt-4o"
            assert redactor.output_key is None
            assert redactor.tools == []
            assert "{clasificacion}" in redactor.instruction
            assert "{similares}" in redactor.instruction
            assert "requiere más información" in redactor.instruction
            assert "aplicación o equipo" in redactor.instruction.lower()
            assert "desde cuándo" in redactor.instruction.lower()
            assert "cuántas personas" in redactor.instruction.lower()
            assert redactor.before_model_callback == app.agent.before_model_callback
            assert redactor.after_model_callback == app.agent.after_model_callback
            assert redactor.generate_content_config.max_output_tokens == 1500
 
            # Los especialistas no transfieren a otros agentes
            for especialista in sub_agents:
                assert especialista.disallow_transfer_to_parent is True
                assert especialista.disallow_transfer_to_peers is True
 
            # 4. Agente de consultas
            consultas = root.sub_agents[1]
            assert isinstance(consultas, LlmAgent)
            assert isinstance(consultas.model, LiteLlm)
            assert consultas.model.model == "openai/gpt-4o-mini"
            assert consultas.tools == [estadisticas_historial]
            assert "estadisticas_historial" in consultas.instruction
            assert consultas.description, "consultas necesita descripción para el enrutado"
            assert consultas.disallow_transfer_to_parent is True
            assert consultas.disallow_transfer_to_peers is True
            assert consultas.before_model_callback == app.agent.before_model_callback
            assert consultas.after_model_callback == app.agent.after_model_callback
            assert consultas.generate_content_config.max_output_tokens == 500
 
            # Verificar objeto App
            assert app.agent.app is not None
            assert app.agent.app.root_agent is root