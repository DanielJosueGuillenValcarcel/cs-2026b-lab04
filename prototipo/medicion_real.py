"""Reto A: medición real del camino lectura → alerta con Mosquitto, PostgreSQL y el código de src/.

Prototipo mínimo: un broker Mosquitto real, el `ConsumidorMqtt` y el `ServicioIngesta` del monolito
guardando en PostgreSQL, un worker de alertas con cola prioritaria y un canal que respeta el límite
de Telegram (20 mensajes/min). Un generador propio (paho-mqtt) reproduce la reconexión de 400 sensores
tras un corte de 2 h. Se mide la latencia real de las alertas en vivo y se compara con fitness/alertas.py.

Uso: python -m prototipo.medicion_real "host=localhost user=postgres" [segundos]
"""
from __future__ import annotations

import json
import pathlib
import queue
import random
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid5, NAMESPACE_DNS

import psycopg2
from psycopg2.extras import execute_values

from airemisti.alertas.dominio import CanalAlertas, RepositorioAlertas
from airemisti.alertas.servicio import ServicioAlertas
from airemisti.ingesta.consumidor import ConsumidorMqtt
from airemisti.ingesta.servicio import ServicioIngesta
from airemisti.lecturas.dominio import RepositorioLecturas
from airemisti.sensores.dominio import RepositorioSensores, Sensor, Ubicacion
from fitness import broker as fb

SENSORES, DISTRITOS = 400, 29
INTERVALO_TELEGRAM_S = 3.0
PM10_EN_VIVO = 190


class LecturasPostgres(RepositorioLecturas):
    def __init__(self, dsn):
        self.conn = psycopg2.connect(dsn)
        with self.conn.cursor() as c:
            c.execute("DROP TABLE IF EXISTS lectura_proto; CREATE TABLE lectura_proto (sensor_id uuid, "
                      "medido_en timestamptz, pm10 numeric(6,1), pm25 numeric(6,1), UNIQUE (sensor_id, medido_en))")
        self.conn.commit()

    def guardar_lote(self, lecturas):
        with self.conn.cursor() as c:
            execute_values(c, "INSERT INTO lectura_proto VALUES %s ON CONFLICT DO NOTHING",
                           [(str(l.sensor_id), l.medido_en, l.pm10, l.pm25) for l in lecturas])
            n = c.rowcount
        self.conn.commit()
        return n


class SensoresMemoria(RepositorioSensores):
    def __init__(self):
        self.datos = {}
        for s in range(SENSORES):
            sensor = Sensor(f"AQP-{s:04d}", Ubicacion(Decimal("-16.4"), Decimal("-71.5"), f"D{s % DISTRITOS:02d}"),
                            id=uuid5(NAMESPACE_DNS, f"AQP-{s:04d}"))
            sensor.dar_de_alta()
            self.datos[sensor.codigo] = sensor

    def buscar_por_codigo(self, codigo):
        return self.datos.get(codigo)

    def guardar(self, s):
        self.datos[s.codigo] = s


class AlertasMemoria(RepositorioAlertas):
    def __init__(self):
        self.vigentes = {}

    def alerta_activa(self, distrito):
        a = self.vigentes.get(distrito)
        return a if a and a.vigente_hasta >= datetime.now(timezone.utc) else None

    def guardar(self, a):
        self.vigentes[a.distrito] = a


class CanalTelegramLimitado(CanalAlertas):
    """Simula el límite del canal: un mensaje cada 3 s; registra la latencia de las alertas en vivo."""

    def __init__(self):
        self.proximo = 0.0
        self.latencias_vivo, self.mensajes = [], 0

    def publicar(self, a):
        espera = self.proximo - time.monotonic()
        if espera > 0:
            time.sleep(espera)
        self.proximo = time.monotonic() + INTERVALO_TELEGRAM_S
        self.mensajes += 1
        primera = a.lecturas[0]
        if primera.pm10 == PM10_EN_VIVO:                 # solo las lecturas en vivo del generador
            self.latencias_vivo.append((datetime.now(timezone.utc) - primera.medido_en).total_seconds())


def ejecutar(politica: str, dsn: str, segundos: int = 150, semilla: int = 7, distritos_vivo: int = 8) -> dict:
    rnd = random.Random(semilla)
    canal = CanalTelegramLimitado()
    alertas = ServicioAlertas(AlertasMemoria(), canal)
    cola = queue.PriorityQueue()
    contador = iter(range(10 ** 9))
    adoptada = politica == "adoptada"

    def encolar(prioridad):
        return lambda l, d: cola.put((prioridad, next(contador), l, d))

    ingesta = ServicioIngesta(SensoresMemoria(), LecturasPostgres(dsn), encolar(0),
                              encolar_historico=None if adoptada else encolar(1))
    if not adoptada:
        ingesta._encolar_picos = lambda lote, distrito, en_vivo: [
            encolar(0)(max(p, key=lambda l: l.pm10), distrito)
            for p in [[l for l in lote if l.pm10 > 150]] if p]

    def worker():
        while True:
            _, _, lectura, distrito = cola.get()
            if lectura is None:
                return
            alertas.evaluar(lectura, distrito)

    with fb.broker(fb.ajustes_produccion()) as b:
        recibidos = queue.Queue()
        sub, _ = fb._cliente(b, "ingesta", limpia=False,
                             al_mensaje=lambda c, u, m: recibidos.put((m.topic, m.payload)))
        sub.subscribe("airemisti/+/lecturas", qos=1)
        consumidor = ConsumidorMqtt(ingesta, publicar=lambda t, c: sub.publish(t, c, qos=1))
        hilo_ingesta = threading.Thread(target=lambda: [consumidor.al_recibir_mensaje(*recibidos.get())
                                                       for _ in iter(int, 1)], daemon=True)
        hilo_ingesta.start()
        hilo_worker = threading.Thread(target=worker, daemon=True)
        hilo_worker.start()

        pico_corte = set(rnd.sample(range(DISTRITOS), 14))
        pico_vivo = set(rnd.sample(range(DISTRITOS), distritos_vivo))
        inicio = time.monotonic()
        eventos = []
        for s in range(SENSORES):
            t0 = rnd.uniform(0, 60)
            eventos.append((t0, s, True))
            t = t0 + rnd.uniform(0, 60)
            while t < segundos - 40:
                eventos.append((t, s, False))
                t += 60
        eventos.sort()
        pub, _ = fb._cliente(b, "simulador")
        for t, s, backlog in eventos:
            espera = inicio + t - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            ahora = datetime.now(timezone.utc)
            d = s % DISTRITOS
            if backlog:
                pico = 180 if d in pico_corte and rnd.random() < 0.6 else 60
                minuto_pico = rnd.randrange(1, 120)
                datos = [{"pm10": pico if m == minuto_pico else 40, "pm25": 20,
                          "medido_en": (ahora - timedelta(minutes=m)).isoformat()} for m in range(120, 0, -1)]
            else:
                vivo = d in pico_vivo and t > 30
                datos = {"pm10": PM10_EN_VIVO if vivo else 50, "pm25": 20, "medido_en": ahora.isoformat()}
            pub.publish(f"airemisti/AQP-{s:04d}/lecturas", json.dumps(datos), qos=1)
        time.sleep(40)
        cola.put((9, 0, None, None))
        hilo_worker.join(timeout=120)
        pub.disconnect()
        sub.disconnect()

    return {"politica": politica, "semilla": semilla, "mensajes_telegram": canal.mensajes,
            "latencias_vivo_s": sorted(canal.latencias_vivo)}


def resumir(corridas: list[dict]) -> dict:
    lat = sorted(x for c in corridas for x in c["latencias_vivo_s"])
    p = lambda q: lat[int(q * (len(lat) - 1))]
    return {"corridas": len(corridas), "alertas_en_vivo": len(lat), "p50_s": p(0.5), "p95_s": p(0.95),
            "max_s": lat[-1], "mensajes_telegram_promedio": sum(c["mensajes_telegram"] for c in corridas) / len(corridas)}


if __name__ == "__main__":
    from fitness import alertas as sim

    dsn = sys.argv[1] if len(sys.argv) > 1 else "host=localhost user=postgres"
    segundos = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    semillas = range(int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    esc = sim.Escenario(distritos_con_pico_en_vivo=8, duracion_s=segundos - 40)
    r = {}
    for nombre, pol in (("vigencia", sim.VIGENCIA), ("adoptada", sim.ADOPTADA)):
        corridas = [ejecutar(nombre, dsn, segundos, semilla) for semilla in semillas]
        lat = sorted(x for k in range(200) for x in [sim.simular(pol, esc, k)["p95_s"]])
        r[nombre] = {"medido": resumir(corridas), "corridas": corridas,
                     "simulado": {"p95_s_promedio": sum(lat) / len(lat), "p95_s_peor": lat[-1]}}
        print(nombre, r[nombre]["medido"], r[nombre]["simulado"], flush=True)
    salida = pathlib.Path(__file__).resolve().parent.parent / "fitness" / "datos" / "medicion_real.json"
    salida.write_text(json.dumps(r, indent=2))
