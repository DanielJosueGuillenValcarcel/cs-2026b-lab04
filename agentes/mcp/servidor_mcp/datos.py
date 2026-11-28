"""Datos ficticios para el servidor MCP (Lab 11): 8 sensores en 4 distritos y lecturas horarias
del 20 al 22 de noviembre de 2026. Se generan con una fórmula fija, sin azar, para que las pruebas
y las trazas sean reproducibles. No hay datos personales.

Casos que el servidor debe manejar (RF-02, RF-04 y Lab 10):
- AQP-03 (Cerro Colorado) registra un episodio de polvo el 21/11 de 13:00 a 16:00 (PM10 > 150).
- AQP-05 (Yanahuara) se reconecta el 21/11 a las 09:00 y reenvía 3 lecturas ya recibidas (duplicados).
- AQP-08 (Mariano Melgar) no tiene canal de PM2.5 (pm25 = None).
- AQP-06 (Yanahuara) está en MANTENIMIENTO desde el 22/11: no envía lecturas ese día.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from airemisti.reportes.resumen import Medicion


@dataclass(frozen=True)
class SensorFicticio:
    codigo: str
    distrito: str
    ubicacion: str
    estado: str


SENSORES = [
    SensorFicticio("AQP-01", "Cayma", "Plaza de Cayma", "ACTIVO"),
    SensorFicticio("AQP-02", "Cayma", "Av. Ejército cuadra 7", "ACTIVO"),
    SensorFicticio("AQP-03", "Cerro Colorado", "Av. Aviación km 3", "ACTIVO"),
    SensorFicticio("AQP-04", "Cerro Colorado", "Parque Industrial Río Seco", "ACTIVO"),
    SensorFicticio("AQP-05", "Yanahuara", "Mirador de Yanahuara", "ACTIVO"),
    SensorFicticio("AQP-06", "Yanahuara", "Av. Bolognesi", "MANTENIMIENTO"),
    SensorFicticio("AQP-07", "Mariano Melgar", "Parque Mariano Melgar", "ACTIVO"),
    SensorFicticio("AQP-08", "Mariano Melgar", "Av. Simón Bolívar", "ACTIVO"),
]
INICIO, DIAS = date(2026, 11, 20), 3


def _pm10(i: int, dia: int, hora: int) -> Decimal:
    base = 38 + 6 * i + (14 if 7 <= hora <= 9 or 18 <= hora <= 20 else 0) + 3 * dia
    if i == 2 and dia == 1 and 13 <= hora <= 16:          # episodio de polvo en AQP-03
        base = 160 + 18 * (hora - 13)
    return Decimal(str(round(base + (hora * 7 % 5) * 1.3, 1)))


def _mediciones() -> list[Medicion]:
    filas = []
    for i, s in enumerate(SENSORES):
        for d in range(DIAS):
            dia = INICIO + timedelta(days=d)
            if s.estado == "MANTENIMIENTO" and d == 2:
                continue
            for hora in range(24):
                pm10 = _pm10(i, d, hora)
                pm25 = None if s.codigo == "AQP-08" else (pm10 * Decimal("0.42")).quantize(Decimal("0.1"))
                filas.append(Medicion(s.codigo, datetime(dia.year, dia.month, dia.day, hora), pm10, pm25))
    reenviadas = [m for m in filas if m.sensor == "AQP-05" and m.medido_en.date() == date(2026, 11, 21)
                  and 6 <= m.medido_en.hour <= 8]
    return filas + reenviadas                              # RF-02: el sensor reenvía tras el corte


MEDICIONES = _mediciones()
