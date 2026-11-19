"""Tarea B del Lab 09: explicación pública de una alerta con un prompt versionado.

Defensa en capas: (1) validar y limpiar la entrada, (2) plantilla con delimitadores,
(3) contrato JSON Schema, (4) severidad recalculada en código y (5) guardrails del texto público.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft7Validator

from monitoreo.ia import GuardrailRechazo, ProveedorLLM, SinConsejosMedicos

PROMPTS = Path(__file__).resolve().parents[2] / "prompts" / "alertas"
NIVELES = ((420.0, "EMERGENCIA"), (350.0, "PELIGRO"), (250.0, "CUIDADO"), (150.0, "MODERADA"))
REFERENCIAS = (150.0, 250.0, 350.0, 420.0, 100.0, 50.0)
CONCENTRACION = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*(?:µg/m³|µg/m3|μg/m³|μg/m3|ug/m3|microgramos)", re.IGNORECASE)
ENLACE = re.compile(r"https?://|www\.", re.IGNORECASE)
CAMPOS_TEXTO = ("sensor", "distrito", "ubicacion", "medido_en")
ESPANOL = re.compile(r"\b(el|la|los|las|que|de|en|un|una|por|con|del|hoy|tu)\b", re.IGNORECASE)
INGLES = re.compile(r"\b(the|and|is|in|of|to|your|with|air|today)\b", re.IGNORECASE)


class EntradaInvalida(ValueError):
    pass


class SalidaInvalida(ValueError):
    pass


def severidad(pm10: float, pm25: float | None = None) -> str:
    if pm10 < 0 or pm10 > 1000 or (pm25 is not None and pm25 > pm10):
        return "INDETERMINADA"
    return next((nombre for limite, nombre in NIVELES if pm10 > limite), "SIN_ALERTA")


def _numero(valor, campo: str) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise EntradaInvalida(f"{campo} debe ser numérico y se recibió {valor!r}") from None


def _limpiar(texto) -> str:
    return re.sub(r"[<>\r\n]", " ", str(texto))[:120].strip()


def preparar_entrada(datos: dict) -> dict:
    entrada = {campo: _limpiar(datos[campo]) for campo in CAMPOS_TEXTO}
    entrada["pm10"] = _numero(datos["pm10"], "pm10")
    entrada["pm25"] = None if datos.get("pm25") is None else _numero(datos["pm25"], "pm25")
    return entrada


class GeneradorExplicacion:
    def __init__(self, proveedor: ProveedorLLM, version: str = "v3"):
        self._proveedor = proveedor
        self._plantilla = (PROMPTS / f"{version}.txt").read_text(encoding="utf-8")
        self._esquema = Draft7Validator(json.loads((PROMPTS / "esquema.json").read_text(encoding="utf-8")))
        self.version = version

    def explicar(self, alerta_id: str, datos: dict) -> dict:
        entrada = preparar_entrada(datos)
        texto = self._proveedor.completar(self.renderizar(alerta_id, entrada))
        return self._validar(alerta_id, texto, entrada)

    def renderizar(self, alerta_id: str, entrada: dict) -> str:
        valores = dict(entrada, id=_limpiar(alerta_id), pm10=f"{entrada['pm10']:.1f}",
                       pm25="sin dato" if entrada["pm25"] is None else f"{entrada['pm25']:.1f}")
        return re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: str(valores[m.group(1)]), self._plantilla)

    def _validar(self, alerta_id: str, texto: str, entrada: dict) -> dict:
        try:
            salida = json.loads(texto)
        except json.JSONDecodeError as e:
            raise SalidaInvalida(f"{self.version}/{alerta_id}: la respuesta no es JSON ({e.msg})") from e
        errores = [e.message for e in self._esquema.iter_errors(salida)]
        if errores:
            raise SalidaInvalida(f"{self.version}/{alerta_id}: no cumple el esquema: {errores[0]}")
        esperada = severidad(entrada["pm10"], entrada["pm25"])
        if salida["severidad"] != esperada:
            raise SalidaInvalida(f"{self.version}/{alerta_id}: severidad {salida['severidad']}, la tabla da {esperada}")
        for parte in (salida["explicacion"], *salida["precauciones"]):
            if len(INGLES.findall(parte)) > len(ESPANOL.findall(parte)):
                raise SalidaInvalida(f"{self.version}/{alerta_id}: la explicación no está en español")
        self._revisar_texto(" ".join([salida["explicacion"], *salida["precauciones"]]), entrada, alerta_id)
        return salida

    def _revisar_texto(self, publico: str, entrada: dict, alerta_id: str):
        permitidos = [v for v in (entrada["pm10"], entrada["pm25"]) if v is not None] + list(REFERENCIAS)
        for m in CONCENTRACION.finditer(publico):
            valor = float(m.group(1).replace(",", "."))
            if all(abs(valor - p) > 0.05 for p in permitidos):
                raise SalidaInvalida(f"{self.version}/{alerta_id}: valor no proporcionado ({m.group(0)})")
        if ENLACE.search(publico):
            raise SalidaInvalida(f"{self.version}/{alerta_id}: la explicación contiene un enlace")
        try:
            SinConsejosMedicos().validar(publico, None)
        except GuardrailRechazo as e:
            raise SalidaInvalida(f"{self.version}/{alerta_id}: {e}") from e
