import json
import re

PROHIBIDAS = re.compile(
    r"\b(mqtt|mosquitto|broker|django|postgres\w*|redis|celery|kafka|endpoints?|api|tablas?|"
    r"base de datos|qos|json|sql)\b",
    re.IGNORECASE,
)


def _json(output):
    try:
        datos = json.loads(output)
    except (TypeError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def _resultado(ok, motivo):
    return {"pass": ok, "score": 1.0 if ok else 0.0, "reason": motivo}


def a2_exito_y_error(output, context):
    if context["vars"].get("esperado") != "valida":
        return _resultado(True, "No aplica: la historia no es válida")
    datos = _json(output)
    if datos is None:
        return _resultado(False, "La salida no es un objeto JSON")
    if datos.get("invest_ok") is not True:
        return _resultado(False, "Rechazó una historia válida")
    tipos = [e.get("tipo") for e in datos.get("escenarios", []) if isinstance(e, dict)]
    if "exito" not in tipos:
        return _resultado(False, "Falta un escenario de éxito")
    if not {"error", "borde"} & set(tipos):
        return _resultado(False, "Falta un escenario de error o de borde")
    return _resultado(True, f"Escenarios: {tipos}")


def a3_sin_implementacion(output, context):
    if context["vars"].get("esperado") == "no_invest":
        return _resultado(True, "No aplica: no debe tener escenarios (lo verifica A4)")
    datos = _json(output)
    texto = json.dumps(datos.get("escenarios", []), ensure_ascii=False) if datos else str(output)
    hallazgos = sorted({m.group(0).lower() for m in PROHIBIDAS.finditer(texto)})
    if hallazgos:
        return _resultado(False, f"Detalles de implementación: {hallazgos}")
    return _resultado(True, "Sin detalles de implementación")


def a4_rechaza_no_invest(output, context):
    datos = _json(output)
    if datos is None:
        return _resultado(False, "La salida no es un objeto JSON")
    preguntas = datos.get("preguntas") or []
    if datos.get("invest_ok") is not False:
        return _resultado(False, "Aceptó una historia que no cumple INVEST")
    if not 1 <= len(preguntas) <= 3:
        return _resultado(False, f"Se esperaban de 1 a 3 preguntas y hay {len(preguntas)}")
    if datos.get("escenarios"):
        return _resultado(False, "Inventó escenarios para una historia no válida")
    return _resultado(True, f"Rechazada con {len(preguntas)} preguntas")
