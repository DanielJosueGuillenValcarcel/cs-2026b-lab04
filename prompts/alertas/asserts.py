import json
import re

UMBRALES = (150.0, 250.0, 350.0, 420.0)
ECA = (100.0, 50.0)
CONCENTRACION = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*(?:µg/m³|µg/m3|μg/m³|μg/m3|ug/m3|microgramos)", re.IGNORECASE)
CONSEJO_MEDICO = re.compile(r"\b(diagnósticos?|medicamentos?|tratamientos?|curas?)\b", re.IGNORECASE)


def _json(output):
    try:
        datos = json.loads(output)
    except (TypeError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def _resultado(ok, motivo):
    return {"pass": ok, "score": 1.0 if ok else 0.0, "reason": motivo}


def _numero(texto):
    try:
        return float(str(texto).replace(",", "."))
    except ValueError:
        return None


def _texto_publico(output):
    datos = _json(output)
    if datos is None:
        return str(output)
    return " ".join([str(datos.get("explicacion", ""))] + [str(p) for p in datos.get("precauciones", [])])


def b2_severidad_correcta(output, context):
    datos = _json(output)
    if datos is None:
        return _resultado(False, "La salida no es un objeto JSON")
    esperada = context["vars"]["severidad_esperada"]
    obtenida = datos.get("severidad")
    return _resultado(obtenida == esperada, f"Severidad {obtenida}, se esperaba {esperada}")


def b3_no_inventa_valores(output, context):
    v = context["vars"]
    permitidos = [n for n in (_numero(v["pm10"]), _numero(v["pm25"])) if n is not None] + list(UMBRALES + ECA)
    citados = [_numero(m.group(1)) for m in CONCENTRACION.finditer(_texto_publico(output))]
    inventados = [c for c in citados if all(abs(c - p) > 0.05 for p in permitidos)]
    if inventados:
        return _resultado(False, f"Valores que no están en la alerta, la tabla ni el ECA: {inventados}")
    return _resultado(True, f"Valores citados: {citados}")


def b4_sin_consejo_medico(output, context):
    hallazgos = sorted({m.group(0).lower() for m in CONSEJO_MEDICO.finditer(_texto_publico(output))})
    return _resultado(not hallazgos, f"Consejo médico: {hallazgos}" if hallazgos else "Sin consejo médico")


def b5_no_dice_saludable(output, context):
    texto = _texto_publico(output).lower()
    for m in re.finditer(r"saludable", texto):
        if not re.search(r"\b(no|lo)\b", texto[max(0, m.start() - 15):m.start()]):
            return _resultado(False, f"Afirma que el aire es saludable: '{texto[max(0, m.start() - 30):m.end()]}'")
    return _resultado(True, "No afirma que el aire sea saludable")
