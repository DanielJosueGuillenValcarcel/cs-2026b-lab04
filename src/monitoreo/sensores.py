"""Adapter + Factory + Decorator para leer los payloads de cada marca."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass
class Lectura:
    codigo: str
    pm10: float
    pm25: float
    medido_en: datetime


class LecturaDescartada(Exception):
    pass


class LectorSensor(Protocol):
    def leer(self, codigo: str, payload) -> Lectura: ...


class AireSenseAdapter:
    """Adapter: AireSense manda JSON con µg/m³ y fecha ISO 8601."""

    def leer(self, codigo, payload):
        return Lectura(codigo, float(payload["pm10"]), float(payload["pm25"]),
                       datetime.fromisoformat(payload["ts"]))


class PurairAdapter:
    """Adapter: Purair manda texto 'PM10=..;PM2_5=..;T=..' en décimas y epoch UTC."""

    def leer(self, codigo, payload):
        if not isinstance(payload, str):
            raise ValueError("Purair espera un payload de texto")
        partes = dict(p.split("=") for p in payload.split(";"))
        return Lectura(codigo, int(partes["PM10"]) / 10, int(partes["PM2_5"]) / 10,
                       datetime.fromtimestamp(int(partes["T"]), tz=timezone.utc))


class FiltroAnomalias:
    """Decorator: envuelve cualquier lector y descarta valores físicamente imposibles."""

    def __init__(self, lector: LectorSensor, pm10_max: float = 1000):
        self.lector = lector
        self.pm10_max = pm10_max

    def leer(self, codigo, payload):
        l = self.lector.leer(codigo, payload)
        if l.pm10 < 0 or l.pm25 < 0 or l.pm10 > self.pm10_max or l.pm25 > l.pm10:
            raise LecturaDescartada(f"Lectura anómala de {codigo}")
        return l


class FabricaLectores:
    """Factory con registro: una marca nueva se agrega sin tocar el servicio.

    Cada servicio recibe su propia fábrica (inyección), no hay registro global.
    """

    def __init__(self, adaptadores: dict[str, type] | None = None):
        self._registro = dict(adaptadores or {"AIRESENSE": AireSenseAdapter, "PURAIR": PurairAdapter})

    def registrar(self, marca: str, adaptador: type):
        self._registro[marca] = adaptador

    def crear(self, marca: str) -> LectorSensor:
        try:
            return FiltroAnomalias(self._registro[marca]())
        except KeyError:
            raise ValueError(f"Marca de sensor no soportada: {marca}") from None
