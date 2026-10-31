"""Fitness functions de calidad (Lab 08): los escenarios del árbol de utilidad convertidos en pruebas.

Las estructurales (FF-01 a FF-04) están en .importlinter. Las que usan Mosquitto real se saltan si el
ejecutable no está instalado en la PC; en la GitHub Action se instala y no se pueden saltar.
"""
import os

import pytest

from fitness import alertas, broker, fiabilidad

PRESUPUESTO_ALERTA_S = 60          # QA-02: alerta visible en ≤ 60 s (p95)
PRESUPUESTO_BACKLOG_S = 300        # QA-01: backlog procesado en ≤ 5 min
SENSORES = 400

# En la integración continua (variable CI) estas pruebas nunca se saltan: si falta Mosquitto, fallan.
requiere_mosquitto = pytest.mark.skipif(not broker.disponible() and "CI" not in os.environ,
                                        reason="Mosquitto no está instalado")


def test_ff05_alerta_en_vivo_en_60_s_durante_la_reconexion_masiva():
    r = alertas.monte_carlo(alertas.ADOPTADA, corridas=50)
    assert r["p95_peor_corrida_s"] <= PRESUPUESTO_ALERTA_S, r


def test_ff06_backlog_de_400_sensores_procesado_en_5_min():
    r = alertas.simular(alertas.ADOPTADA, alertas.Escenario(dispersion_reconexion_s=0))
    assert r["backlog_procesado_s"] <= PRESUPUESTO_BACKLOG_S, r


def test_ff07_cero_lecturas_perdidas_en_un_mes():
    assert fiabilidad.monte_carlo(fiabilidad.ADOPTADA, meses=300)["media"] == 0


def test_ff08_configuracion_del_broker():
    ajustes = dict(l.split(maxsplit=1) for l in broker.ajustes_produccion())
    conf = broker.CONF_PRODUCCION.read_text()
    assert "allow_anonymous false" in conf
    assert ajustes["persistence"] == "true"
    assert int(ajustes.get("max_queued_messages", 1000)) >= SENSORES * 120, "la cola no cubre 2 h de caída de la ingesta"
    escrituras = [l for l in broker.ACL_PRODUCCION.read_text().splitlines() if "write" in l and not l.startswith("#")]
    assert all("%u" in l or "/ack" in l for l in escrituras), "un sensor podría escribir en el tema de otro"


@requiere_mosquitto
def test_ff09_cero_lecturas_perdidas_con_la_ingesta_caida_10_min():
    r = broker.experimento_caida_ingesta(broker.ajustes_produccion(), sensores=SENSORES, minutos=10)
    assert r["perdidas"] == 0, r


@requiere_mosquitto
def test_ff10_el_acuse_recupera_lo_que_pierde_una_caida_del_broker():
    r = broker.experimento_acuse(broker.ajustes_produccion(), sensores=SENSORES, minutos=1)
    assert r["perdidas"] == 0 and r["sin_confirmar"] == 0, r


@requiere_mosquitto
def test_ff11_un_sensor_no_puede_suplantar_a_otro():
    r = broker.experimento_acl()
    assert r["propias_aceptadas"] == 1
    assert r["suplantaciones_aceptadas"] == 0
    assert r["anonimo_rechazado"] and r["clave_incorrecta_rechazada"]


@requiere_mosquitto
def test_ff12_alta_de_50_sensores_sin_reiniciar_el_broker():
    r = broker.experimento_alta_sensores(existentes=SENSORES, nuevos=50)
    assert r["conectados"] == 50 and r["lecturas_recibidas"] == 50
    assert not r["ingesta_desconectada"]
