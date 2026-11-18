"""Proveedor de promptfoo que devuelve respuestas grabadas en lugar de llamar a un modelo.

Configuración (relativa a la carpeta prompts/):
  plantillas: carpeta con las versiones del prompt (v1.txt, v2.txt, ...)
  grabaciones: carpeta con una subcarpeta por versión y un <id>.txt por caso
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VARIABLE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def renderizar(plantilla, variables):
    return VARIABLE.sub(lambda m: str(variables.get(m.group(1), "")), plantilla)


def detectar_version(prompt, variables, carpeta, etiqueta=None):
    versiones = {p.stem: p for p in sorted(carpeta.glob("v*.txt"))}
    if etiqueta in versiones:
        return etiqueta
    for nombre, ruta in versiones.items():
        if renderizar(ruta.read_text(encoding="utf-8"), variables).strip() == prompt.strip():
            return nombre
    return None


def leer_grabacion(config, prompt, variables, etiqueta=None):
    version = detectar_version(prompt, variables, RAIZ / config["plantillas"], etiqueta)
    if version is None:
        raise LookupError("El prompt no coincide con ninguna versión de " + config["plantillas"])
    ruta = RAIZ / config["grabaciones"] / version / f"{variables['id']}.txt"
    if not ruta.exists():
        raise FileNotFoundError(f"Falta la grabación {ruta.relative_to(RAIZ)}")
    return ruta.read_text(encoding="utf-8")


def call_api(prompt, options, context):
    config = options.get("config", {})
    variables = context.get("vars", {})
    etiqueta = (context.get("prompt") or {}).get("label")
    try:
        return {"output": leer_grabacion(config, prompt, variables, etiqueta)}
    except (LookupError, OSError) as e:
        return {"error": str(e)}
