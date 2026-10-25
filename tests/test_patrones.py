"""Pruebas de que cada patrón cumple lo que promete (extensión sin tocar el servicio)."""
from datetime import datetime

import pytest

from monitoreo.estados import TransicionInvalida
from monitoreo.eventos import ConReintentos, PublicadorEventos, SuscriptorBase
from monitoreo.externos import TelegramBotSimulado, payload_airesense
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


# --- State: ciclo de vida del sensor ---------------------------------------------
@pytest.mark.parametrize("pasos, final", [
    (["marcar_sin_senal"], "SIN_SENAL"),
    (["marcar_sin_senal", "iniciar_sincronizacion"], "SINCRONIZANDO"),
    (["marcar_sin_senal", "iniciar_sincronizacion", "completar_sincronizacion"], "ACTIVO"),
    (["marcar_sin_senal", "iniciar_sincronizacion", "marcar_sin_senal"], "SIN_SENAL"),
    (["enviar_a_mantenimiento", "reactivar"], "ACTIVO"),
    (["enviar_a_mantenimiento", "dar_de_baja"], "BAJA"),
    (["marcar_sin_senal", "dar_de_baja"], "BAJA"),
    (["marcar_sin_senal", "registrar_lectura"], "ACTIVO"),
])
def test_transiciones_del_diagrama_de_estados(pasos, final):
    s = Sensor("AQP-07", "Cayma", "AIRESENSE")
    for paso in pasos:
        getattr(s, paso)()
    assert s.estado == final


@pytest.mark.parametrize("pasos, invalido", [
    ([], "dar_de_baja"),
    ([], "reactivar"),
    (["enviar_a_mantenimiento"], "registrar_lectura"),
    (["enviar_a_mantenimiento", "dar_de_baja"], "reactivar"),
    (["marcar_sin_senal", "iniciar_sincronizacion"], "registrar_lectura"),
])
def test_transiciones_fuera_del_diagrama_fallan(pasos, invalido):
    s = Sensor("AQP-07", "Cayma", "AIRESENSE")
    for paso in pasos:
        getattr(s, paso)()
    antes = s.estado
    with pytest.raises(TransicionInvalida):
        getattr(s, invalido)()
    assert s.estado == antes


# --- Observer: suscriptor nuevo sin tocar el servicio -----------------------------
def test_suscriptor_nuevo_recibe_las_alertas():
    class Contador(SuscriptorBase):
        alertas = 0

        def alerta_abierta(self, alerta):
            Contador.alertas += 1

    pub = PublicadorEventos()
    pub.suscribir(Contador())
    s = ServicioMonitoreo(publicador=pub)
    s.registrar_sensor(Sensor("AQP-07", "Cayma", "AIRESENSE"))
    s.procesar("AQP-07", payload_airesense(180, 60, T0))
    assert Contador.alertas == 1


# --- Decorator: reintentos -------------------------------------------------------
def test_reintentos_no_ocultan_errores_que_no_son_de_red():
    class Roto:
        llamadas = 0

        def enviar(self, texto):
            Roto.llamadas += 1
            raise PermissionError("token inválido")

    with pytest.raises(PermissionError):
        ConReintentos(Roto()).enviar("hola")
    assert Roto.llamadas == 1


def test_reintentos_se_rinden_tras_el_limite():
    class Caido:
        def enviar(self, texto):
            raise ConnectionError

    with pytest.raises(ConnectionError):
        ConReintentos(Caido(), intentos=2).enviar("hola")


def test_telegram_recibe_el_texto_de_la_alerta_por_el_adapter():
    bot = TelegramBotSimulado()
    s = ServicioMonitoreo(telegram=bot)
    s.registrar_sensor(Sensor("AQP-07", "Cayma", "AIRESENSE"))
    s.procesar("AQP-07", payload_airesense(180, 60, T0))
    assert bot.enviados[0][0] == "@airemisti_alertas"
