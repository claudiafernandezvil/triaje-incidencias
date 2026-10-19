"""Script de evaluación del agente clasificador de incidencias.

Ejecuta de manera aislada el agente `clasificador` con una sesión en memoria
por cada caso definido en `tests/eval/casos_evaluacion.json`.
Compara los resultados obtenidos con los esperados, reporta precisión por campo
y por conjunto ('ajuste' y 'nuevo'), calcula el consumo de tokens y costes FinOps,
y guarda el resultado detallado en `tests/eval/ultimo_resultado.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

# Asegurar que la raíz del proyecto está en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Carga variables de entorno antes de importar el agente
load_dotenv()

from app.agent import clasificador, modelo_sencillo
from app.finops import calcular_coste

CASOS_FILE = ROOT_DIR / "tests" / "eval" / "casos_evaluacion.json"
RESULTADO_FILE = ROOT_DIR / "tests" / "eval" / "ultimo_resultado.md"


@dataclass
class ResultadoCaso:
    """Almacena el resultado de la evaluación de un caso individual."""

    id_caso: str
    conjunto: str
    incidencia: str
    requiere_mas_informacion: bool
    # Esperados
    categoria_esperada: str | None
    impacto_esperado: str | None
    urgencia_esperada: str | None
    prioridad_esperada: str | None
    # Obtenidos
    categoria_obtenida: str | None = None
    impacto_obtenido: str | None = None
    urgencia_obtenido: str | None = None
    prioridad_obtenida: str | None = None
    llamo_herramienta: bool = False
    texto_respuesta: str = ""
    # Validación
    categoria_ok: bool = False
    impacto_ok: bool = False
    urgencia_ok: bool = False
    prioridad_ok: bool = False
    es_correcto: bool = False
    fallos: list[str] = field(default_factory=list)
    # Consumo
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    coste_usd: float = 0.0


def extraer_categoria_de_texto(texto: str) -> str | None:
    """Extrae la categoría del texto final del clasificador usando regex.

    Busca líneas con formato 'Categoría: <valor>' o variaciones en mayúsculas/minúsculas
    y formato Markdown (ej. '**Categoría:** Red').
    """
    if not texto:
        return None

    patron = r"(?:^|\n)[-*\s]*\*{0,2}Categor[íi]a\*{0,2}\s*:\s*([^\n\r]+)"
    match = re.search(patron, texto, re.IGNORECASE)
    if not match:
        return None

    valor = match.group(1).strip()
    # Eliminar formato markdown como asteriscos, comillas y puntos finales
    valor_limpio = re.sub(r"[*_`'\"]", "", valor).strip().rstrip(".")
    valor_lower = valor_limpio.lower()

    if "requiere m" in valor_lower or "requiere mas" in valor_lower:
        return "requiere más información"

    for cat in ["Red", "Software", "Hardware", "Accesos"]:
        if cat.lower() == valor_lower or cat.lower() in valor_lower:
            return cat

    return valor_limpio


def ejecutar_caso(caso: dict[str, Any]) -> ResultadoCaso:
    """Ejecuta un caso individual de evaluación con el Runner de ADK."""
    id_caso = caso.get("id", "DESCONOCIDO")
    conjunto = caso.get("conjunto", "desconocido")
    incidencia = caso.get("incidencia", "")
    esperado = caso.get("esperado", {})
    requiere_mas_info = bool(esperado.get("requiere_mas_informacion", False))

    resultado = ResultadoCaso(
        id_caso=id_caso,
        conjunto=conjunto,
        incidencia=incidencia,
        requiere_mas_informacion=requiere_mas_info,
        categoria_esperada="requiere más información" if requiere_mas_info else esperado.get("categoria"),
        impacto_esperado=esperado.get("impacto"),
        urgencia_esperada=esperado.get("urgencia"),
        prioridad_esperada=esperado.get("prioridad"),
    )

    # Sesión limpia en memoria por caso
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        user_id=f"eval_user_{id_caso}", app_name="eval_clasificador"
    )
    runner = Runner(
        agent=clasificador,
        session_service=session_service,
        app_name="eval_clasificador",
    )

    mensaje = types.Content(
        role="user", parts=[types.Part.from_text(text=incidencia)]
    )

    events = list(
        runner.run(
            new_message=mensaje,
            user_id=f"eval_user_{id_caso}",
            session_id=session.id,
        )
    )

    # 1. Extraer llamadas a herramientas, respuestas, texto final y tokens
    for event in events:
        # Metadatos de tokens
        usage = getattr(event, "usage_metadata", None)
        if usage:
            resultado.prompt_tokens += getattr(usage, "prompt_token_count", 0) or 0
            resultado.completion_tokens += getattr(usage, "candidates_token_count", 0) or 0

        # Llamadas a herramientas (impacto y urgencia de los argumentos)
        for call in event.get_function_calls():
            if call.name == "calcular_prioridad":
                resultado.llamo_herramienta = True
                args = call.args or {}
                raw_imp = args.get("impacto")
                raw_urg = args.get("urgencia")
                resultado.impacto_obtenido = (
                    str(raw_imp).strip().capitalize() if raw_imp else None
                )
                resultado.urgencia_obtenido = (
                    str(raw_urg).strip().capitalize() if raw_urg else None
                )

        # Respuesta de la herramienta (prioridad)
        for resp in event.get_function_responses():
            if resp.name == "calcular_prioridad":
                datos_resp = resp.response or {}
                raw_pri = datos_resp.get("prioridad")
                resultado.prioridad_obtenida = (
                    str(raw_pri).strip().upper() if raw_pri else None
                )

        # Texto acumulado de respuesta
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    resultado.texto_respuesta += part.text + "\n"

    resultado.total_tokens = resultado.prompt_tokens + resultado.completion_tokens
    resultado.coste_usd = calcular_coste(
        modelo_sencillo, resultado.prompt_tokens, resultado.completion_tokens
    )

    # 2. Extraer categoría del texto final
    resultado.categoria_obtenida = extraer_categoria_de_texto(resultado.texto_respuesta)

    # 3. Validar aciertos
    if resultado.requiere_mas_informacion:
        # Para casos con requiere_mas_informacion=true:
        # Es correcto si NO llama a calcular_prioridad y la respuesta indica que necesita más información.
        no_llamo = not resultado.llamo_herramienta
        indica_mas_info = (
            (resultado.categoria_obtenida == "requiere más información")
            or ("requiere más información" in resultado.texto_respuesta.lower())
            or ("más información" in resultado.texto_respuesta.lower())
        )

        resultado.categoria_ok = (resultado.categoria_obtenida == "requiere más información")
        resultado.impacto_ok = no_llamo
        resultado.urgencia_ok = no_llamo
        resultado.prioridad_ok = no_llamo

        if not no_llamo:
            resultado.fallos.append(
                f"Llamó a calcular_prioridad(impacto='{resultado.impacto_obtenido}', "
                f"urgencia='{resultado.urgencia_obtenido}') cuando no debía llamar."
            )
        if not indica_mas_info:
            resultado.fallos.append(
                f"No indicó que requiere más información. Categoría obtenida: '{resultado.categoria_obtenida}'."
            )

        resultado.es_correcto = no_llamo and indica_mas_info

    else:
        # Para casos estándar: comparar categoría, impacto, urgencia y prioridad
        resultado.categoria_ok = resultado.categoria_obtenida == resultado.categoria_esperada
        resultado.impacto_ok = resultado.impacto_obtenido == resultado.impacto_esperado
        resultado.urgencia_ok = resultado.urgencia_obtenido == resultado.urgencia_esperada
        resultado.prioridad_ok = resultado.prioridad_obtenida == resultado.prioridad_esperada

        if not resultado.categoria_ok:
            resultado.fallos.append(
                f"Categoría: esperado='{resultado.categoria_esperada}', obtenido='{resultado.categoria_obtenida}'"
            )
        if not resultado.impacto_ok:
            resultado.fallos.append(
                f"Impacto: esperado='{resultado.impacto_esperado}', obtenido='{resultado.impacto_obtenido}'"
            )
        if not resultado.urgencia_ok:
            resultado.fallos.append(
                f"Urgencia: esperado='{resultado.urgencia_esperada}', obtenido='{resultado.urgencia_obtenido}'"
            )
        if not resultado.prioridad_ok:
            resultado.fallos.append(
                f"Prioridad: esperado='{resultado.prioridad_esperada}', obtenido='{resultado.prioridad_obtenida}'"
            )

        resultado.es_correcto = (
            resultado.categoria_ok
            and resultado.impacto_ok
            and resultado.urgencia_ok
            and resultado.prioridad_ok
        )

    return resultado


def generar_reporte_markdown(
    resultados: list[ResultadoCaso],
    fecha_utc: str,
    modelo: str,
) -> str:
    """Genera el contenido en formato Markdown para tests/eval/ultimo_resultado.md."""
    total_casos = len(resultados)
    casos_ajuste = [r for r in resultados if r.conjunto == "ajuste"]
    casos_nuevo = [r for r in resultados if r.conjunto == "nuevo"]

    correctos_total = sum(1 for r in resultados if r.es_correcto)
    correctos_ajuste = sum(1 for r in casos_ajuste if r.es_correcto)
    correctos_nuevo = sum(1 for r in casos_nuevo if r.es_correcto)

    pct_total = (correctos_total / total_casos * 100) if total_casos else 0.0
    pct_ajuste = (correctos_ajuste / len(casos_ajuste) * 100) if casos_ajuste else 0.0
    pct_nuevo = (correctos_nuevo / len(casos_nuevo) * 100) if casos_nuevo else 0.0

    # Aciertos por campo en casos estándar
    estandar = [r for r in resultados if not r.requiere_mas_informacion]
    n_estandar = len(estandar)
    cat_ok = sum(1 for r in estandar if r.categoria_ok)
    imp_ok = sum(1 for r in estandar if r.impacto_ok)
    urg_ok = sum(1 for r in estandar if r.urgencia_ok)
    pri_ok = sum(1 for r in estandar if r.prioridad_ok)

    pct_cat = (cat_ok / n_estandar * 100) if n_estandar else 0.0
    pct_imp = (imp_ok / n_estandar * 100) if n_estandar else 0.0
    pct_urg = (urg_ok / n_estandar * 100) if n_estandar else 0.0
    pct_pri = (pri_ok / n_estandar * 100) if n_estandar else 0.0

    # Tokens y costes
    total_prompt = sum(r.prompt_tokens for r in resultados)
    total_completion = sum(r.completion_tokens for r in resultados)
    total_tokens = sum(r.total_tokens for r in resultados)
    total_coste = sum(r.coste_usd for r in resultados)

    lineas: list[str] = []
    lineas.append("# Último Resultado de Evaluación del Clasificador")
    lineas.append("")
    lineas.append(f"- **Fecha (UTC):** {fecha_utc}")
    lineas.append(f"- **Modelo evaluado:** `{modelo}`")
    lineas.append(f"- **Total de casos evaluados:** {total_casos}")
    lineas.append("")

    lineas.append("## 1. Resumen de Aciertos")
    lineas.append("")
    lineas.append("| Métrica | Aciertos | Porcentaje |")
    lineas.append("| :--- | :---: | :---: |")
    lineas.append(f"| **Casos totalmente correctos (Global)** | {correctos_total}/{total_casos} | {pct_total:.1f}% |")
    lineas.append(f"| Conjunto `ajuste` | {correctos_ajuste}/{len(casos_ajuste)} | {pct_ajuste:.1f}% |")
    lineas.append(f"| Conjunto `nuevo` | {correctos_nuevo}/{len(casos_nuevo)} | {pct_nuevo:.1f}% |")
    lineas.append("")

    lineas.append("### Precisión por Campo (Casos Estándar)")
    lineas.append("")
    lineas.append("| Campo | Aciertos | Porcentaje |")
    lineas.append("| :--- | :---: | :---: |")
    lineas.append(f"| Categoría | {cat_ok}/{n_estandar} | {pct_cat:.1f}% |")
    lineas.append(f"| Impacto | {imp_ok}/{n_estandar} | {pct_imp:.1f}% |")
    lineas.append(f"| Urgencia | {urg_ok}/{n_estandar} | {pct_urg:.1f}% |")
    lineas.append(f"| Prioridad | {pri_ok}/{n_estandar} | {pct_pri:.1f}% |")
    lineas.append("")

    lineas.append("## 2. Consumo y Costes FinOps")
    lineas.append("")
    lineas.append("| Concepto | Cantidad |")
    lineas.append("| :--- | :---: |")
    lineas.append(f"| Tokens de entrada (prompt) | {total_prompt:,} |")
    lineas.append(f"| Tokens de salida (completion) | {total_completion:,} |")
    lineas.append(f"| Tokens totales | {total_tokens:,} |")
    lineas.append(f"| Coste total estimado | **${total_coste:.6f} USD** |")
    lineas.append("")

    lineas.append("## 3. Tabla de Fallos")
    lineas.append("")
    fallos = [r for r in resultados if not r.es_correcto]
    if not fallos:
        lineas.append("✅ **¡No se detectaron fallos! Todos los casos se resolvieron como se esperaba.**")
    else:
        lineas.append("| ID | Conjunto | Incidencia | Discrepancias (Esperado vs Obtenido) |")
        lineas.append("| :---: | :---: | :--- | :--- |")
        for f in fallos:
            desc_corta = (f.incidencia[:50] + "...") if len(f.incidencia) > 50 else f.incidencia
            detalles_fallo = "<br>".join(f.fallos)
            lineas.append(f"| {f.id_caso} | `{f.conjunto}` | {desc_corta} | {detalles_fallo} |")
    lineas.append("")

    lineas.append("## 4. Detalle de Ejecución por Caso")
    lineas.append("")
    lineas.append("| ID | Conjunto | Categoría (Esp / Obt) | Impacto (Esp / Obt) | Urgencia (Esp / Obt) | Prioridad (Esp / Obt) | Estado | Tokens | Coste ($) |")
    lineas.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in resultados:
        estado_icono = "✅ OK" if r.es_correcto else "❌ Fallo"
        cat_str = f"{r.categoria_esperada} / {r.categoria_obtenida}"
        imp_str = f"{r.impacto_esperado or '-'} / {r.impacto_obtenido or '-'}"
        urg_str = f"{r.urgencia_esperada or '-'} / {r.urgencia_obtenido or '-'}"
        pri_str = f"{r.prioridad_esperada or '-'} / {r.prioridad_obtenida or '-'}"
        lineas.append(
            f"| {r.id_caso} | `{r.conjunto}` | {cat_str} | {imp_str} | {urg_str} | {pri_str} | {estado_icono} | {r.total_tokens} | ${r.coste_usd:.6f} |"
        )
    lineas.append("")

    return "\n".join(lineas)


def imprimir_resumen_pantalla(
    resultados: list[ResultadoCaso],
    fecha_utc: str,
    modelo: str,
) -> None:
    """Muestra el informe de evaluación formateado en consola."""
    total_casos = len(resultados)
    casos_ajuste = [r for r in resultados if r.conjunto == "ajuste"]
    casos_nuevo = [r for r in resultados if r.conjunto == "nuevo"]

    correctos_total = sum(1 for r in resultados if r.es_correcto)
    correctos_ajuste = sum(1 for r in casos_ajuste if r.es_correcto)
    correctos_nuevo = sum(1 for r in casos_nuevo if r.es_correcto)

    pct_total = (correctos_total / total_casos * 100) if total_casos else 0.0
    pct_ajuste = (correctos_ajuste / len(casos_ajuste) * 100) if casos_ajuste else 0.0
    pct_nuevo = (correctos_nuevo / len(casos_nuevo) * 100) if casos_nuevo else 0.0

    estandar = [r for r in resultados if not r.requiere_mas_informacion]
    n_estandar = len(estandar)
    cat_ok = sum(1 for r in estandar if r.categoria_ok)
    imp_ok = sum(1 for r in estandar if r.impacto_ok)
    urg_ok = sum(1 for r in estandar if r.urgencia_ok)
    pri_ok = sum(1 for r in estandar if r.prioridad_ok)

    pct_cat = (cat_ok / n_estandar * 100) if n_estandar else 0.0
    pct_imp = (imp_ok / n_estandar * 100) if n_estandar else 0.0
    pct_urg = (urg_ok / n_estandar * 100) if n_estandar else 0.0
    pct_pri = (pri_ok / n_estandar * 100) if n_estandar else 0.0

    total_prompt = sum(r.prompt_tokens for r in resultados)
    total_completion = sum(r.completion_tokens for r in resultados)
    total_tokens = sum(r.total_tokens for r in resultados)
    total_coste = sum(r.coste_usd for r in resultados)

    sep = "=" * 78
    sub_sep = "-" * 78

    print("\n" + sep)
    print("             EVALUACIÓN DEL AGENTE CLASIFICADOR (ADK RUNNER)")
    print(sep)
    print(f" Fecha: {fecha_utc} UTC")
    print(f" Modelo: {modelo}")
    print(f" Total de casos: {total_casos}")
    print(sub_sep)

    print("\n[+] PORCENTAJE DE ACIERTO POR CAMPO (Casos estándar):")
    print(f"  * Categoría: {pct_cat:5.1f}%  ({cat_ok}/{n_estandar})")
    print(f"  * Impacto:   {pct_imp:5.1f}%  ({imp_ok}/{n_estandar})")
    print(f"  * Urgencia:  {pct_urg:5.1f}%  ({urg_ok}/{n_estandar})")
    print(f"  * Prioridad: {pct_pri:5.1f}%  ({pri_ok}/{n_estandar})")

    print("\n[+] CASOS TOTALMENTE CORRECTOS:")
    print(f"  * Conjunto 'ajuste': {pct_ajuste:5.1f}%  ({correctos_ajuste}/{len(casos_ajuste)})")
    print(f"  * Conjunto 'nuevo':  {pct_nuevo:5.1f}%  ({correctos_nuevo}/{len(casos_nuevo)})")
    print(f"  * Total Global:     {pct_total:5.1f}%  ({correctos_total}/{total_casos})")

    print("\n[+] CONSUMO DE TOKENS Y COSTE:")
    print(f"  * Tokens entrada (prompt):     {total_prompt:,}")
    print(f"  * Tokens salida (completion):  {total_completion:,}")
    print(f"  * Tokens totales:              {total_tokens:,}")
    print(f"  * Coste total estimado:        ${total_coste:.6f} USD")

    fallos = [r for r in resultados if not r.es_correcto]
    print("\n" + sub_sep)
    if not fallos:
        print("[+] TABLA DE FALLOS: ¡Ninguno! Todos los casos son correctos.")
    else:
        print(f"[!] TABLA DE FALLOS ({len(fallos)} casos con discrepancias):")
        print(f"{'ID':<6} | {'Conjunto':<8} | {'Discrepancias (Esperado vs Obtenido)'}")
        print("-" * 78)
        for f in fallos:
            for i, fallo_desc in enumerate(f.fallos):
                id_col = f.id_caso if i == 0 else ""
                conj_col = f.conjunto if i == 0 else ""
                print(f"{id_col:<6} | {conj_col:<8} | {fallo_desc}")
    print(sep + "\n")


def main() -> None:
    """Punto de entrada principal para la evaluación del clasificador."""
    if not CASOS_FILE.exists():
        print(f"Error: No se encontró el archivo de casos en {CASOS_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(CASOS_FILE, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    casos = data.get("casos", [])
    total_casos = len(casos)
    fecha_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    print(f"\nIniciando evaluación de {total_casos} casos con modelo '{modelo_sencillo}'...")
    print("Ejecutando únicamente el agente 'clasificador' por caso con sesión en memoria...\n")

    resultados: list[ResultadoCaso] = []
    for idx, caso in enumerate(casos, 1):
        id_caso = caso.get("id", f"caso_{idx}")
        conjunto = caso.get("conjunto", "")
        print(f"  [{idx:02d}/{total_casos:02d}] Evaluando {id_caso} ({conjunto})...", end="", flush=True)

        res = ejecutar_caso(caso)
        resultados.append(res)

        estado_str = "OK" if res.es_correcto else "FALLO"
        print(f" -> {estado_str} ({res.total_tokens} tokens)")

    # Mostrar resumen por pantalla
    imprimir_resumen_pantalla(resultados, fecha_utc, modelo_sencillo)

    # Guardar en tests/eval/ultimo_resultado.md
    contenido_md = generar_reporte_markdown(resultados, fecha_utc, modelo_sencillo)
    RESULTADO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTADO_FILE, mode="w", encoding="utf-8") as f:
        f.write(contenido_md)

    print(f"Resultados guardados en: {RESULTADO_FILE}\n")


if __name__ == "__main__":
    main()
