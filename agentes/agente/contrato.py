"""Contrato estructurado de cada decisión del modelo (se valida ANTES de consultar la política).

Una decisión válida es exactamente una de estas dos formas:
  {"pensamiento": str, "accion": <herramienta del catálogo>, "args": dict}
  {"pensamiento": str, "final": str}
"""


def validar_decision(d, herramientas_conocidas) -> tuple[bool, str]:
    if not isinstance(d, dict):
        return False, "la decisión debe ser un objeto JSON"
    if not isinstance(d.get("pensamiento"), str) or not d["pensamiento"].strip():
        return False, "falta 'pensamiento' (texto no vacío)"
    if ("final" in d) == ("accion" in d):
        return False, "debe incluir 'accion' o 'final', pero no ambos"
    if "final" in d:
        return (True, "") if isinstance(d["final"], str) else (False, "'final' debe ser texto")
    if d["accion"] not in herramientas_conocidas:
        return False, f"herramienta desconocida: {d['accion']!r}"
    if not isinstance(d.get("args", {}), dict):
        return False, "'args' debe ser un objeto JSON"
    extra = set(d) - {"pensamiento", "accion", "args"}
    return (False, f"campos no permitidos: {sorted(extra)}") if extra else (True, "")
