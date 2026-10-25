"""Strategy: la norma con la que se clasifica una lectura (ECA Perú u OMS 2021)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormaCalidad:
    nombre: str
    pm10_limite: float
    pm25_limite: float

    def clasificar(self, lectura) -> str:
        cumple = lectura.pm10 <= self.pm10_limite and lectura.pm25 <= self.pm25_limite
        return "CUMPLE" if cumple else "EXCEDE"


ECA = NormaCalidad("ECA", 100, 50)
OMS = NormaCalidad("OMS", 45, 15)


class FabricaNormas:
    def __init__(self, normas: tuple[NormaCalidad, ...] = (ECA, OMS)):
        self._registro = {n.nombre: n for n in normas}

    def registrar(self, norma: NormaCalidad):
        self._registro[norma.nombre] = norma

    def crear(self, nombre: str) -> NormaCalidad:
        try:
            return self._registro[nombre]
        except KeyError:
            raise ValueError(f"Norma no soportada: {nombre}") from None
