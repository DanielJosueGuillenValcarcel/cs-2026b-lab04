"""Pruebas de que cada patrón cumple lo que promete (extensión sin tocar el servicio)."""
from datetime import datetime

import pytest

from monitoreo.externos import payload_airesense
from monitoreo.indices import ECA, FabricaNormas, NormaCalidad, OMS
from monitoreo.sensores import FabricaLectores, FiltroAnomalias, Lectura, LecturaDescartada
from monitoreo.servicio import Sensor, ServicioMonitoreo

T0 = "2026-10-20T10:00:00+00:00"


# --- Adapter + Factory: marca nueva sin modificar ServicioMonitoreo ---------------
class AirQAdapter:
    def leer(self, codigo, payload):
        pm10, pm25, ts = payload
        return Lectura(codigo, pm10, pm25, datetime.fromisoformat(ts))


def test_marca_nueva_se_registra_sin_tocar_el_servicio():
    fabrica = FabricaLectores()
    fabrica.registrar("AIRQ", AirQAdapter)
    s = ServicioMonitoreo(lectores=fabrica)
    s.registrar_sensor(Sensor("AQP-99", "Yanahuara", "AIRQ"))
    assert s.procesar("AQP-99", (30, 10, T0)) == "GUARDADA"


def test_la_fabrica_siempre_envuelve_con_el_filtro_de_anomalias():
    assert isinstance(FabricaLectores().crear("AIRESENSE"), FiltroAnomalias)
    with pytest.raises(ValueError, match="no soportada"):
        FabricaLectores().crear("XIAOMI")


def test_cada_servicio_tiene_su_propia_fabrica():
    una = FabricaLectores()
    una.registrar("AIRQ", AirQAdapter)
    with pytest.raises(ValueError):
        FabricaLectores().crear("AIRQ")


# --- Decorator: filtro de anomalías ----------------------------------------------
def test_filtro_de_anomalias_es_configurable():
    class Fijo:
        def leer(self, codigo, payload):
            return Lectura(codigo, 600, 100, datetime.fromisoformat(T0))

    assert FiltroAnomalias(Fijo()).leer("X", None).pm10 == 600
    with pytest.raises(LecturaDescartada):
        FiltroAnomalias(Fijo(), pm10_max=500).leer("X", None)


# --- Strategy: norma de calidad ---------------------------------------------------
def test_estrategias_eca_y_oms_clasifican_distinto():
    l = Lectura("X", 60, 20, None)
    assert (ECA.clasificar(l), OMS.clasificar(l)) == ("CUMPLE", "EXCEDE")


def test_norma_nueva_se_agrega_sin_tocar_el_servicio():
    normas = FabricaNormas()
    normas.registrar(NormaCalidad("ESTRICTA", 20, 10))
    s = ServicioMonitoreo(norma="ESTRICTA", normas=normas)
    s.registrar_sensor(Sensor("AQP-07", "Cayma", "AIRESENSE"))
    s.procesar("AQP-07", payload_airesense(30, 5, T0))
    assert s.eventos == ["mapa:AQP-07:EXCEDE"]
