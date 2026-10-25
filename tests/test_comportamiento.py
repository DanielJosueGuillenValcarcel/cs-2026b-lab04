import importlib
from datetime import datetime, timezone

import pytest

from monitoreo.externos import (ClienteGeminiSimulado, ClienteOpenAISimulado, TelegramBotSimulado,
                                payload_airesense, payload_purair)

VERSIONES = ["monitoreo.antes.servicio"]
T0 = "2026-10-20T10:00:00+00:00"
T1 = "2026-10-20T10:01:00+00:00"


@pytest.fixture(params=VERSIONES)
def m(request):
    return importlib.import_module(request.param)


def servicio(m, *, marca="AIRESENSE", norma="ECA", telegram=None):
    s = m.ServicioMonitoreo(telegram=telegram or TelegramBotSimulado(), norma=norma)
    s.registrar_sensor(m.Sensor("AQP-07", "Cayma", marca))
    return s


def test_lectura_normal_se_guarda_y_actualiza_el_mapa(m):
    s = servicio(m)
    assert s.procesar("AQP-07", payload_airesense(40, 20, T0)) == "GUARDADA"
    assert s.eventos == ["mapa:AQP-07:CUMPLE"]


def test_lectura_purair_se_convierte_a_microgramos(m):
    s = servicio(m, marca="PURAIR")
    epoch = int(datetime(2026, 10, 20, 10, tzinfo=timezone.utc).timestamp())
    assert s.procesar("AQP-07", payload_purair(180.5, 60.2, epoch)) == "GUARDADA"
    assert [l.pm10 for l in s.lecturas.values()] == [180.5]
    assert "analista:Cayma:180.5" in s.eventos


def test_pm10_sobre_umbral_publica_alerta_y_avisa_al_analista(m):
    bot = TelegramBotSimulado()
    s = servicio(m, telegram=bot)
    s.procesar("AQP-07", payload_airesense(180, 60, T0))
    texto = "Alerta de calidad del aire en Cayma: PM10 = 180.0 µg/m³."
    assert s.eventos == ["mapa:AQP-07:EXCEDE", f"telegram:{texto}", "analista:Cayma:180.0"]
    assert bot.enviados == [("@airemisti_alertas", texto)]


def test_alerta_vigente_se_extiende_sin_repetir_el_aviso(m):
    bot = TelegramBotSimulado()
    s = servicio(m, telegram=bot)
    s.procesar("AQP-07", payload_airesense(180, 60, T0))
    s.procesar("AQP-07", payload_airesense(210, 70, T1))
    assert len(bot.enviados) == 1
    assert s.alertas["Cayma"].pm10_max == 210


@pytest.mark.parametrize("pm10, pm25", [(-5, 2), (40, 60), (1500, 80)])
def test_lectura_anomala_se_descarta_sin_eventos(m, pm10, pm25):
    s = servicio(m)
    assert s.procesar("AQP-07", payload_airesense(pm10, pm25, T0)) == "DESCARTADA"
    assert s.eventos == [] and not s.lecturas


def test_lectura_repetida_no_se_duplica(m):
    s = servicio(m)
    s.procesar("AQP-07", payload_airesense(40, 20, T0))
    assert s.procesar("AQP-07", payload_airesense(40, 20, T0)) == "DUPLICADA"
    assert len(s.lecturas) == 1


def test_sensor_de_baja_se_rechaza(m):
    s = servicio(m)
    sensor = s.sensores["AQP-07"]
    sensor.marcar_sin_senal()
    sensor.dar_de_baja()
    with pytest.raises(ValueError):
        s.procesar("AQP-07", payload_airesense(180, 60, T0))
    assert not s.lecturas and s.eventos == []


def test_sensor_sin_senal_vuelve_a_activo(m):
    s = servicio(m)
    s.sensores["AQP-07"].marcar_sin_senal()
    s.procesar("AQP-07", payload_airesense(40, 20, T0))
    assert s.sensores["AQP-07"].estado == "ACTIVO"


def test_reintenta_telegram_tras_dos_fallas(m):
    bot = TelegramBotSimulado(fallas=2)
    s = servicio(m, telegram=bot)
    s.procesar("AQP-07", payload_airesense(180, 60, T0))
    assert bot.llamadas == 3 and len(bot.enviados) == 1


def test_telegram_caido_registra_el_fallo(m):
    s = servicio(m, telegram=TelegramBotSimulado(fallas=5))
    s.procesar("AQP-07", payload_airesense(180, 60, T0))
    assert "telegram_fallido:Cayma" in s.eventos


def test_norma_oms_es_mas_estricta_que_eca(m):
    eca, oms = servicio(m, norma="ECA"), servicio(m, norma="OMS")
    eca.procesar("AQP-07", payload_airesense(60, 20, T0))
    oms.procesar("AQP-07", payload_airesense(60, 20, T0))
    assert eca.eventos == ["mapa:AQP-07:CUMPLE"] and oms.eventos == ["mapa:AQP-07:EXCEDE"]


def test_payload_invalido_no_reactiva_un_sensor_sin_senal(m, request):
    if "antes" in request.node.callspec.id:
        request.applymarker(pytest.mark.xfail(reason="Error de la versión antes: cambia el estado antes de leer el payload", strict=True))
    s = servicio(m)
    s.sensores["AQP-07"].marcar_sin_senal()
    with pytest.raises((KeyError, ValueError)):
        s.procesar("AQP-07", {"temperatura": 20})
    assert s.sensores["AQP-07"].estado == "SIN_SENAL"


EXPLICACION = "En Cayma el aire está muy contaminado: el PM10 llegó a 180.0 µg/m³. Evite hacer deporte al aire libre."


@pytest.mark.parametrize("proveedor, cliente", [("OPENAI", ClienteOpenAISimulado), ("GEMINI", ClienteGeminiSimulado)])
def test_ia_explica_la_alerta_con_cualquier_proveedor(m, proveedor, cliente):
    s = servicio(m)
    s.procesar("AQP-07", payload_airesense(180, 60, T0))
    assert s.explicar_alerta("Cayma", proveedor, cliente(EXPLICACION)) == EXPLICACION


@pytest.mark.parametrize("respuesta", [
    "En Cayma el PM10 llegó a 350 µg/m³, un récord histórico.",
    "En Cayma el aire está contaminado; tome un medicamento para la tos.",
    "El aire en Cayma está contaminado. " * 15,
])
def test_guardrails_bloquean_respuestas_inseguras_de_la_ia(m, respuesta):
    s = servicio(m)
    s.procesar("AQP-07", payload_airesense(180, 60, T0))
    with pytest.raises(ValueError, match="Guardrail"):
        s.explicar_alerta("Cayma", "OPENAI", ClienteOpenAISimulado(respuesta))

