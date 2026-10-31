"""Simulación de eventos discretos del camino lectura → alerta pública (QA-01 y QA-02).

Escenario de crecimiento: 400 sensores vuelven a conectarse a la vez tras un corte de red de 2 h
ocurrido durante un episodio de contaminación. Cada sensor reenvía su backlog (120 lecturas en un
mensaje) y luego sigue enviando una lectura por minuto. En algunos distritos el episodio continúa:
sus lecturas en vivo superan 150 µg/m³ y la alerta debe publicarse en ≤ 60 s (p95).

Etapas: broker → proceso de ingesta (1 consumidor) → cola de Celery (n workers) → canal de
Telegram. Supuestos (documentados en docs/architecture/add/iteracion-1.md):
- Ingesta: lote de 120 lecturas con mediana 6 ms; lectura suelta con mediana 1 ms
  (calibrado con fitness/calibrar_bd.py en PostgreSQL 16 y multiplicado por 2 por el ORM de Django).
- Evaluación de la alerta en el worker: mediana 20 ms.
- Telegram: un canal acepta 20 mensajes por minuto (FAQ de bots); el exceso espera su turno.
"""
from __future__ import annotations

import heapq
import math
import random
import statistics
from dataclasses import dataclass, field

VIGENCIA_S = 3600


@dataclass(frozen=True)
class Politica:
    nombre: str
    workers: int = 2
    corrige_vigencia: bool = False      # Alerta.extender no acorta la vigencia con lecturas antiguas
    solo_frescas: bool = False          # lecturas con más de 10 min no generan alerta pública
    prioridad_vivo: bool = False        # cola "alertas" separada de la cola "historico"
    ventana_frescura_s: int = 600


ACTUAL = Politica("Actual (Lab 05)")
MAS_WORKERS = Politica("8 workers", workers=8)
VIGENCIA = Politica("Vigencia corregida", corrige_vigencia=True)
ADOPTADA = Politica("Frescura + cola prioritaria", corrige_vigencia=True, solo_frescas=True, prioridad_vivo=True)
POLITICAS = [ACTUAL, MAS_WORKERS, VIGENCIA, ADOPTADA]


@dataclass(frozen=True)
class Escenario:
    sensores: int = 400
    distritos: int = 29
    corte_s: int = 7200
    distritos_con_pico_en_corte: int = 14
    distritos_con_pico_en_vivo: int = 3
    dispersion_reconexion_s: float = 60.0
    mensajes_por_minuto_telegram: int = 20
    duracion_s: int = 600


def _lognormal(rnd, mediana, p95):
    sigma = math.log(p95 / mediana) / 1.645
    return rnd.lognormvariate(math.log(mediana), sigma)


@dataclass(order=True)
class _Tarea:
    prioridad: int
    llegada: float
    distrito: int = field(compare=False)
    medido_en: float = field(compare=False)
    en_vivo: bool = field(compare=False)


def simular(politica: Politica, esc: Escenario = Escenario(), semilla: int = 7) -> dict:
    rnd = random.Random(semilla)
    distrito_de = [s % esc.distritos for s in range(esc.sensores)]
    pico_corte = set(rnd.sample(range(esc.distritos), esc.distritos_con_pico_en_corte))
    pico_vivo = set(rnd.sample(range(esc.distritos), esc.distritos_con_pico_en_vivo))

    mensajes = []                                   # (llegada al broker, sensor, es_backlog, medido_en, pm10_max)
    for s in range(esc.sensores):
        t0 = rnd.uniform(0, esc.dispersion_reconexion_s)
        d = distrito_de[s]
        pico = 180.0 if d in pico_corte and rnd.random() < 0.6 else 60.0
        mensajes.append((t0, s, True, t0 - rnd.uniform(60, esc.corte_s), pico))
        t = t0 + rnd.uniform(0, 60)
        while t < esc.duracion_s:
            pm10 = 190.0 if d in pico_vivo and t > 30 else 50.0
            mensajes.append((t, s, False, t, pm10))
            t += 60
    mensajes.sort()

    tareas, libre_ingesta, fin_backlog = [], 0.0, 0.0
    for llegada, s, backlog, medido_en, pm10 in mensajes:
        inicio = max(llegada, libre_ingesta)
        libre_ingesta = inicio + (_lognormal(rnd, 0.006, 0.012) if backlog else _lognormal(rnd, 0.001, 0.002))
        if backlog:
            fin_backlog = max(fin_backlog, libre_ingesta)
        if pm10 <= 150:
            continue
        fresca = libre_ingesta - medido_en <= politica.ventana_frescura_s
        if politica.solo_frescas and not fresca:
            continue                                # va a la cola "historico": aviso al analista, no al canal
        prioridad = 0 if (politica.prioridad_vivo and fresca) else 1
        tareas.append(_Tarea(prioridad if politica.prioridad_vivo else 0, libre_ingesta, distrito_de[s], medido_en, not backlog))

    tareas.sort(key=lambda x: x.llegada)
    workers = [0.0] * politica.workers
    heapq.heapify(workers)
    cola, i, vigente_hasta, publicaciones = [], 0, {}, []
    while i < len(tareas) or cola:
        ahora = workers[0]
        while i < len(tareas) and (tareas[i].llegada <= ahora or not cola):
            heapq.heappush(cola, tareas[i])
            i += 1
        tarea = heapq.heappop(cola)
        libre = heapq.heappop(workers)
        inicio = max(libre, tarea.llegada)
        fin = inicio + _lognormal(rnd, 0.020, 0.050)
        heapq.heappush(workers, fin)
        hasta = vigente_hasta.get(tarea.distrito, -1e9)
        if hasta >= fin:
            nueva = tarea.medido_en + VIGENCIA_S
            vigente_hasta[tarea.distrito] = max(hasta, nueva) if politica.corrige_vigencia else nueva
        else:
            vigente_hasta[tarea.distrito] = fin + VIGENCIA_S
            publicaciones.append((fin, tarea))

    intervalo = 60 / esc.mensajes_por_minuto_telegram
    proximo, latencias_vivo, enviados = 0.0, [], 0
    cola_canal, j, t = [], 0, 0.0
    pendientes_por_llegada = sorted(publicaciones, key=lambda x: x[0])
    while j < len(pendientes_por_llegada) or cola_canal:
        if not cola_canal:
            t = max(t, pendientes_por_llegada[j][0])
        while j < len(pendientes_por_llegada) and pendientes_por_llegada[j][0] <= t:
            fin, tarea = pendientes_por_llegada[j]
            heapq.heappush(cola_canal, ((tarea.prioridad if politica.prioridad_vivo else 0), fin, j, tarea))
            j += 1
        _, fin, _, tarea = heapq.heappop(cola_canal)
        envio = max(t, proximo)
        proximo = envio + intervalo
        t = envio
        enviados += 1
        if tarea.en_vivo:
            latencias_vivo.append(envio - tarea.medido_en)

    latencias_vivo.sort()
    p = (lambda q: latencias_vivo[int(q * (len(latencias_vivo) - 1))]) if latencias_vivo else (lambda q: 0.0)
    return {"politica": politica.nombre, "mensajes_telegram": enviados, "alertas_en_vivo": len(latencias_vivo),
            "p50_s": p(0.50), "p95_s": p(0.95), "max_s": p(1.0), "backlog_procesado_s": fin_backlog}


def monte_carlo(politica: Politica, esc: Escenario = Escenario(), corridas: int = 200) -> dict:
    rs = [simular(politica, esc, semilla) for semilla in range(corridas)]
    lat = sorted(r["p95_s"] for r in rs)
    return {"politica": politica.nombre,
            "p95_s": statistics.mean(lat),
            "p95_peor_corrida_s": lat[-1],
            "mensajes_telegram": statistics.mean(r["mensajes_telegram"] for r in rs),
            "backlog_procesado_s": max(r["backlog_procesado_s"] for r in rs)}


if __name__ == "__main__":
    for pol in POLITICAS:
        print(monte_carlo(pol, corridas=100))
