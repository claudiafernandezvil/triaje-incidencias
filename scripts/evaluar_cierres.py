"""Evaluación del agente gestion_tickets: ¿cierra solo con soluciones válidas?
 
Crea una base de datos de evaluación nueva, registra varios tickets y envía al
agente gestion_tickets mensajes de cierre con soluciones válidas y no válidas
(absurdas, sin relación con la incidencia o vagas). Después comprueba en la base
de datos si cada ticket quedó cerrado o abierto.
 
Este script llama a OpenAI: no forma parte de los tests unitarios.
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
 
# Base de datos propia de esta evaluación, vacía en cada ejecución.
RUTA_BD_EVAL = ROOT_DIR / "logs" / "soporte_eval_cierres.db"
RUTA_BD_EVAL.parent.mkdir(parents=True, exist_ok=True)
RUTA_BD_EVAL.unlink(missing_ok=True)
os.environ["RUTA_BD"] = str(RUTA_BD_EVAL)
 
from app.agent import gestion_tickets  # noqa: E402
from app.tickets import registrar_incidencia, ver_ticket  # noqa: E402
 
# (descripción, categoría, impacto, urgencia, solución propuesta, debe_cerrarse, tipo)
CASOS = [
    ("La VPN da error de certificado al conectar desde casa", "Red", "Usuario", "Alta",
     "se reinstaló el certificado de usuario desde el portal de autoservicio", True, "válida"),
    ("La impresora de la planta 2 atasca el papel en cada hoja", "Hardware", "Departamento", "Media",
     "se limpiaron los rodillos y se sustituyó la bandeja de alimentación", True, "válida"),
    ("Outlook se queda cargando el perfil y no abre", "Software", "Usuario", "Alta",
     "se reparó el perfil de Outlook desde el panel de control y se volvió a crear", True, "válida"),
    ("No puedo acceder a la carpeta de finanzas, dice acceso denegado", "Accesos", "Usuario", "Media",
     "se añadió al usuario al grupo de seguridad de finanzas tras la aprobación del responsable", True, "válida"),
    ("El portátil no carga la batería", "Hardware", "Usuario", "Alta",
     "se solucionó comiendo una pizza en la sala de descanso", False, "absurda"),
    ("El Wi-Fi de la sala de reuniones se desconecta continuamente", "Red", "Departamento", "Media",
     "el técnico bailó delante del router y ya va", False, "absurda"),
    ("Excel se cierra al abrir un archivo grande", "Software", "Usuario", "Media",
     "se cambió el tóner de la impresora", False, "sin relación"),
    ("Mi cuenta está bloqueada tras varios intentos fallidos", "Accesos", "Usuario", "Alta",
     "ya funciona todo correctamente", False, "vaga"),
]
 
 
def enviar_cierre(id_ticket: str, solucion: str, indice: int) -> None:
    """Envía al agente gestion_tickets un mensaje de cierre en una sesión nueva."""
    user_id = f"eval_cierre_{indice}"
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id=user_id, app_name="eval_cierres")
    runner = Runner(agent=gestion_tickets, session_service=session_service, app_name="eval_cierres")
    mensaje = f"Cierra el ticket {id_ticket}, {solucion}"
    contenido = types.Content(role="user", parts=[types.Part.from_text(text=mensaje)])
    for _ in runner.run(new_message=contenido, user_id=user_id, session_id=session.id):
        pass
 
 
def main() -> None:
    print(f"\nEvaluando el cierre de tickets con {len(CASOS)} casos...\n")
    aciertos = 0
    falsos_cierres = 0   # cerró con una solución no válida (lo más grave)
    falsos_rechazos = 0  # no cerró con una solución válida
 
    for i, (desc, cat, imp, urg, solucion, debe_cerrarse, tipo) in enumerate(CASOS, 1):
        id_ticket = registrar_incidencia(desc, cat, imp, urg)["id"]
        enviar_cierre(id_ticket, solucion, i)
 
        cerrado = ver_ticket(id_ticket).get("estado") == "cerrada"
        ok = cerrado == debe_cerrarse
        aciertos += ok
        if cerrado and not debe_cerrarse:
            falsos_cierres += 1
        if not cerrado and debe_cerrarse:
            falsos_rechazos += 1
 
        esperado = "cerrar" if debe_cerrarse else "rechazar"
        obtenido = "cerrado" if cerrado else "rechazado"
        estado = "OK   " if ok else "FALLO"
        print(f"  [{estado}] {id_ticket} ({tipo:<12}) esperado={esperado:<8} obtenido={obtenido:<9} | {solucion}")
 
    pct = aciertos / len(CASOS) * 100
    print(f"\nDecisiones correctas: {aciertos}/{len(CASOS)} ({pct:.1f}%)")
    print(f"Cierres con solución no válida (falsos cierres): {falsos_cierres}")
    print(f"Soluciones válidas rechazadas (falsos rechazos): {falsos_rechazos}")
    print("Revisa el coste con: uv run python scripts/informe_costes.py\n")
 
 
if __name__ == "__main__":
    main()