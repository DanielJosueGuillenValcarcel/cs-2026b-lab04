"""Tarea A del Lab 09: criterios de aceptación en Gherkin con un prompt versionado."""
from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft7Validator

from monitoreo.ia import ProveedorLLM

PROMPTS = Path(__file__).resolve().parents[2] / "prompts" / "criterios"


class SalidaInvalida(ValueError):
    pass


class GeneradorCriterios:
    def __init__(self, proveedor: ProveedorLLM, version: str = "v3"):
        self._proveedor = proveedor
        self._plantilla = (PROMPTS / f"{version}.txt").read_text(encoding="utf-8")
        self._esquema = Draft7Validator(json.loads((PROMPTS / "esquema.json").read_text(encoding="utf-8")))
        self.version = version

    def generar(self, id_historia: str, historia: str) -> dict:
        valores = {"id": re.sub(r"[<>\"]", "", id_historia), "historia": re.sub(r"[<>]", " ", historia)}
        prompt = re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: valores[m.group(1)], self._plantilla)
        texto = self._proveedor.completar(prompt)
        try:
            criterios = json.loads(texto)
        except json.JSONDecodeError as e:
            raise SalidaInvalida(f"{self.version}/{id_historia}: la respuesta no es JSON ({e.msg})") from e
        errores = [e.message for e in self._esquema.iter_errors(criterios)]
        if errores:
            raise SalidaInvalida(f"{self.version}/{id_historia}: no cumple el esquema: {errores[0]}")
        self._revisar_coherencia(id_historia, criterios)
        return criterios

    def _revisar_coherencia(self, id_historia: str, criterios: dict):
        tipos = {e["tipo"] for e in criterios["escenarios"]}
        if criterios["invest_ok"] and not ("exito" in tipos and tipos & {"error", "borde"}):
            raise SalidaInvalida(f"{self.version}/{id_historia}: faltan escenarios de éxito y de error o borde")
        if not criterios["invest_ok"] and (criterios["escenarios"] or not criterios["preguntas"]):
            raise SalidaInvalida(f"{self.version}/{id_historia}: una historia rechazada solo lleva preguntas")
