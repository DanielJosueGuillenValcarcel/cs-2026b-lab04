"""Mide en PostgreSQL el tiempo de guardar un lote de lecturas (ADR-002).

Uso: python fitness/calibrar_bd.py "host=localhost port=5432 user=postgres"
Crea la tabla `lectura` particionada por mes con clave única (sensor_id, medido_en),
la precarga y mide tres formas de insertar. El resultado se guarda en
fitness/datos/calibracion_bd.json y alimenta la simulación de alertas.
"""
import json
import pathlib
import random
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import execute_values

SQL = """
DROP TABLE IF EXISTS lectura;
CREATE TABLE lectura (sensor_id int, medido_en timestamptz, pm10 numeric(6,1), pm25 numeric(6,1),
                      UNIQUE (sensor_id, medido_en)) PARTITION BY RANGE (medido_en);
CREATE TABLE lectura_2026_10 PARTITION OF lectura FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE lectura_2026_11 PARTITION OF lectura FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE lectura_defecto PARTITION OF lectura DEFAULT;
"""
INSERT = ("INSERT INTO lectura (sensor_id, medido_en, pm10, pm25) VALUES %s "
          "ON CONFLICT (sensor_id, medido_en) DO NOTHING")
INSERT_FILA = ("INSERT INTO lectura (sensor_id, medido_en, pm10, pm25) VALUES (%s, %s, %s, %s) "
               "ON CONFLICT (sensor_id, medido_en) DO NOTHING")
SENSORES, DIAS_PRECARGA = 400, 5
INICIO = datetime(2026, 10, 1, tzinfo=timezone.utc)


def precargar(cur):
    filas = []
    for minuto in range(DIAS_PRECARGA * 1440):
        t = INICIO + timedelta(minutes=minuto)
        filas.extend((s, t, 40.0, 20.0) for s in range(SENSORES))
        if len(filas) >= 50_000:
            execute_values(cur, INSERT, filas, page_size=5000)
            filas = []
    if filas:
        execute_values(cur, INSERT, filas, page_size=5000)


def medir(conn, fn, repeticiones=300):
    tiempos = []
    for _ in range(repeticiones):
        t0 = time.perf_counter()
        with conn.cursor() as cur:
            fn(cur)
        conn.commit()
        tiempos.append((time.perf_counter() - t0) * 1000)
    tiempos.sort()
    return {"mediana_ms": statistics.median(tiempos), "p95_ms": tiempos[int(0.95 * (len(tiempos) - 1))],
            "media_ms": statistics.mean(tiempos)}


def main(dsn):
    rnd = random.Random(7)
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(SQL)
        precargar(cur)
    conn.commit()
    reloj = [INICIO + timedelta(days=DIAS_PRECARGA)]

    def lote(n):
        reloj[0] += timedelta(minutes=n)
        s = rnd.randrange(SENSORES)
        return [(s, reloj[0] - timedelta(minutes=i), rnd.uniform(20, 200), 15.0) for i in range(n)]

    r = {
        "filas_precargadas": SENSORES * DIAS_PRECARGA * 1440,
        "lote_1_lectura": medir(conn, lambda c: execute_values(c, INSERT, lote(1))),
        "lote_120_execute_values": medir(conn, lambda c: execute_values(c, INSERT, lote(120))),
        "lote_120_fila_por_fila": medir(conn, lambda c: [c.execute(INSERT_FILA, f) for f in lote(120)]),
    }
    salida = pathlib.Path(__file__).parent / "datos" / "calibracion_bd.json"
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "host=localhost user=postgres")
