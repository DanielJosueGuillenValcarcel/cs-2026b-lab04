"""Monte Carlo de un mes de operación con 400 sensores (QA-01 y QA-03).

Los parámetros de pérdida salen de los experimentos reales de fitness/broker.py con Mosquitto 2.0.18:
- con los valores por defecto el broker guarda como máximo 1000 mensajes para la ingesta desconectada;
- una caída brusca del broker pierde los mensajes en cola que aún no se guardaron en disco;
- con el acuse de aplicación el sensor reenvía lo que no fue confirmado y no se pierde nada.

Supuestos de frecuencia (iteracion-2.md): 8 caídas de la ingesta al mes (despliegues y errores),
con duración lognormal de mediana 3 min y p95 30 min; 1 caída brusca del VPS al mes.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass

LECTURAS_POR_MIN = 400


@dataclass(frozen=True)
class Config:
    nombre: str
    max_cola: int
    autosave_s: int
    acuse_aplicacion: bool


DEFECTO = Config("Mosquitto por defecto", 1000, 1800, False)
COLA_AMPLIA = Config("Cola de 200 000 + autosave 60 s", 200_000, 60, False)
ADOPTADA = Config("Cola amplia + acuse de aplicación", 200_000, 60, True)
CONFIGS = [DEFECTO, COLA_AMPLIA, ADOPTADA]


def _lognormal(rnd, mediana, p95):
    return rnd.lognormvariate(math.log(mediana), math.log(p95 / mediana) / 1.645)


def simular_mes(cfg: Config, semilla: int = 7, caidas_ingesta: float = 8, caidas_vps: float = 1) -> dict:
    rnd = random.Random(semilla)
    mes = 30 * 24 * 60
    perdidas = 0
    caidas = []
    t = rnd.expovariate(caidas_ingesta / mes)
    while t < mes:
        caidas.append((t, _lognormal(rnd, 3, 30)))
        t += rnd.expovariate(caidas_ingesta / mes)
    for _, dur in caidas:
        en_cola = dur * LECTURAS_POR_MIN
        if not cfg.acuse_aplicacion:
            perdidas += max(0, en_cola - cfg.max_cola)
    t = rnd.expovariate(caidas_vps / mes)
    while t < mes:
        abierta = next(((ini, dur) for ini, dur in caidas if ini <= t <= ini + dur), None)
        if abierta:
            ini, _ = abierta
            minutos_sin_guardar = min(t - ini, cfg.autosave_s / 60 * rnd.random())
            en_riesgo = min(minutos_sin_guardar * LECTURAS_POR_MIN, cfg.max_cola)
        else:
            en_riesgo = LECTURAS_POR_MIN / 60          # lecturas en tránsito en el último segundo
        if not cfg.acuse_aplicacion:
            perdidas += en_riesgo
        t += rnd.expovariate(caidas_vps / mes)
    return {"perdidas": round(perdidas), "caidas_ingesta": len(caidas)}


def monte_carlo(cfg: Config, meses: int = 1000) -> dict:
    ps = sorted(simular_mes(cfg, s)["perdidas"] for s in range(meses))
    return {"config": cfg.nombre, "media": statistics.mean(ps), "p95": ps[int(0.95 * (meses - 1))],
            "meses_con_perdidas": sum(p > 0 for p in ps) / meses}


if __name__ == "__main__":
    for c in CONFIGS:
        print(monte_carlo(c))
