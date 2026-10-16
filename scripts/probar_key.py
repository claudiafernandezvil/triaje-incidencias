""" Comprueba que la API key funciona y lista los modelos disponibles. """
import os
from dotenv import load_dotenv
from openai import OpenAI
 
load_dotenv()
 
client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.getenv("OPENAI_API_BASE"),  
)
 
try:
    modelos = client.models.list()
    print("La key funciona. Modelos disponibles:")
    for m in modelos:
        print("  -", m.id)
except Exception as e:
    print(" Error al conectar:", type(e).__name__, "-", e)

