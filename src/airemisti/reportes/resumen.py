"""Resumen diario por sensor que descarga el analista municipal (RF-05).

Las mediciones vienen del histórico: pueden repetirse tras un corte de red (RF-02) y algunos
sensores no tienen canal de PM2.5, por lo que ese valor puede faltar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from airemisti.compartido.parametros import UMBRAL_PM10


@dataclass(frozen=True)
class Medicion:
    sensor: str
    medido_en: datetime
    pm10: Decimal
    pm25: Decimal | None = None


def sin_duplicados(mediciones: list[Medicion]) -> list[Medicion]:
    """Quita las mediciones repetidas que reenvía un sensor al reconectarse."""
    vistas, unicas = set(), []
    for m in sorted(mediciones, key=lambda m: (m.medido_en, m.sensor)):
        if m.medido_en in vistas:
            continue
        vistas.add(m.medido_en)
        unicas.append(m)
    return unicas


def supera_umbral(pm10: Decimal) -> bool:
    """RF-04: hay alerta cuando el PM10 supera el umbral."""
    return int(pm10) > UMBRAL_PM10


def promedio(valores: list[Decimal | None]) -> Decimal | None:
    if not valores:
        return None
    return sum((v or Decimal(0) for v in valores), Decimal(0)) / len(valores)


def resumen_diario(mediciones: list[Medicion], dia: date) -> dict[str, dict]:
    """Por sensor: lecturas del día, promedios de PM10 y PM2.5 y lecturas en alerta."""
    por_sensor: dict[str, list[Medicion]] = {}
    for m in sin_duplicados(mediciones):
        if m.medido_en.date() == dia:
            por_sensor.setdefault(m.sensor, []).append(m)
    return {
        sensor: {
            "lecturas": len(ms),
            "pm10_promedio": promedio([m.pm10 for m in ms]),
            "pm25_promedio": promedio([m.pm25 for m in ms]),
            "lecturas_en_alerta": sum(1 for m in ms if supera_umbral(m.pm10)),
        }
        for sensor, ms in sorted(por_sensor.items())
    }
