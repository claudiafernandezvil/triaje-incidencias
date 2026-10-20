"""Evaluación del enrutado del agente coordinador.
 
Envía una serie de mensajes al root_agent (coordinador) y comprueba a qué
agente los transfiere: 'triaje' (incidencias nuevas), 'consultas' (preguntas
sobre el historial) o ninguno (el coordinador responde él mismo).
 
Este script llama a OpenAI: no forma parte de los tests unitarios.
Los mensajes enviados a 'triaje' ejecutan la cadena completa, por lo que
cada caso cuesta aproximadamente lo mismo que una incidencia normal.
"""
 
from __future__ import annotations
 
from pathlib import Path
import sys
 
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
 
import os
 
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
 
load_dotenv()
 
# Los tickets creados durante la evaluación se guardan aparte, para no mezclarlos
# con los tickets reales. Debe fijarse antes de ejecutar los agentes.
os.environ["RUTA_TICKETS"] = str(ROOT_DIR / "logs" / "tickets_evaluacion.csv")
 
from app.agent import root_agent  # noqa: E402
 
SIN_TRANSFERENCIA = "coordinador"
 
CASOS = [
    ("La impresora no imprime y tengo que entregar un informe esta tarde", "triaje"),
    ("No funciona", "triaje"),
    ("Necesito acceso a la carpeta compartida de finanzas", "triaje"),
    ("Outlook se cierra cada vez que abro un adjunto", "triaje"),
    ("La VPN va muy lenta cuando trabajo desde casa", "triaje"),
    ("¿Cuántas incidencias de Red hay en el historial?", "consultas"),
    ("¿Qué categoría tiene más incidencias resueltas?", "consultas"),
    ("Dame algunos ejemplos de incidencias de Hardware ya resueltas", "consultas"),
    ("¿Cuántos tickets con prioridad P1 hay abiertos?", "consultas"),
    ("Hola, ¿qué puedes hacer?", SIN_TRANSFERENCIA),
]
 
 
def destino_de(mensaje: str, indice: int) -> str:
    """Ejecuta el coordinador con una sesión nueva y devuelve el primer destino."""
    user_id = f"eval_coord_{indice}"
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        user_id=user_id, app_name="eval_coordinador"
    )
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        app_name="eval_coordinador",
    )
    contenido = types.Content(role="user", parts=[types.Part.from_text(text=mensaje)])
 
    destino = SIN_TRANSFERENCIA
    for event in runner.run(
        new_message=contenido, user_id=user_id, session_id=session.id
    ):
        if destino != SIN_TRANSFERENCIA:
            continue  # ya sabemos el destino; dejamos terminar la ejecución
        for call in event.get_function_calls():
            if call.name == "transfer_to_agent":
                destino = (call.args or {}).get("agent_name", "desconocido")
    return destino
 
 
def main() -> None:
    print(f"\nEvaluando el enrutado del coordinador con {len(CASOS)} mensajes...\n")
    aciertos = 0
    for i, (mensaje, esperado) in enumerate(CASOS, 1):
        obtenido = destino_de(mensaje, i)
        ok = obtenido == esperado
        aciertos += ok
        estado = "OK   " if ok else "FALLO"
        print(f"  [{estado}] esperado={esperado:<11} obtenido={obtenido:<11} | {mensaje}")
 
    pct = aciertos / len(CASOS) * 100
    print(f"\nEnrutado correcto: {aciertos}/{len(CASOS)} ({pct:.1f}%)")
    print("Revisa el coste con: uv run python scripts/informe_costes.py\n")
 
 
if __name__ == "__main__":
    main()