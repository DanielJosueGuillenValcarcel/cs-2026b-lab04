"""Lab 09: los prompts versionados se usan detrás de ProveedorLLM y su salida se valida antes de publicarse."""
import json
from pathlib import Path

import pytest
import yaml

from monitoreo.generador_criterios import GeneradorCriterios
from monitoreo.generador_criterios import SalidaInvalida as CriteriosInvalidos
from monitoreo.generador_explicacion import (EntradaInvalida, GeneradorExplicacion, SalidaInvalida,
                                             preparar_entrada, severidad)
from monitoreo.ia import SinConsejosMedicos

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
ALERTAS = {c["vars"]["id"]: c["vars"] for c in yaml.safe_load((PROMPTS / "alertas/casos.yaml").read_text("utf-8"))}
ATAQUES = {c["vars"]["id"]: c["vars"] for c in
           yaml.safe_load((PROMPTS / "seguridad/ataques-alertas.yaml").read_text("utf-8"))}
HISTORIAS = {c["vars"]["id"]: c["vars"] for c in yaml.safe_load((PROMPTS / "criterios/casos.yaml").read_text("utf-8"))}


class ProveedorGrabado:
    """Devuelve una respuesta grabada del modelo y guarda los prompts que recibió."""

    def __init__(self, respuesta: str):
        self.respuesta = respuesta
        self.prompts: list[str] = []

    def completar(self, prompt):
        self.prompts.append(prompt)
        return self.respuesta


def grabacion(ruta: str) -> str:
    return (PROMPTS / ruta).read_text(encoding="utf-8")


def datos(vars_caso: dict) -> dict:
    d = dict(vars_caso)
    d["pm25"] = None if d["pm25"] == "sin dato" else d["pm25"]
    return d


@pytest.mark.parametrize("pm10, pm25, esperada", [
    (150.0, 60.0, "SIN_ALERTA"), (150.1, 60.0, "MODERADA"), (250.0, 80.0, "MODERADA"), (250.1, 80.0, "CUIDADO"),
    (350.0, 90.0, "CUIDADO"), (420.0, 90.0, "PELIGRO"), (420.1, 90.0, "EMERGENCIA"), (-12.0, 8.0, "INDETERMINADA"),
    (1200.0, 90.0, "INDETERMINADA"), (180.0, 200.0, "INDETERMINADA"), (190.5, None, "MODERADA"),
])
def test_severidad_sigue_la_tabla_del_ds_009_2003_sa(pm10, pm25, esperada):
    assert severidad(pm10, pm25) == esperada


@pytest.mark.parametrize("caso", sorted(ALERTAS))
def test_la_v3_grabada_se_acepta_en_los_9_casos(caso):
    proveedor = ProveedorGrabado(grabacion(f"alertas/grabaciones/v3/{caso}.txt"))
    salida = GeneradorExplicacion(proveedor).explicar(caso, datos(ALERTAS[caso]))
    assert salida["severidad"] == ALERTAS[caso]["severidad_esperada"]


def test_el_prompt_renderizado_por_el_codigo_es_el_que_se_grabo():
    proveedor = ProveedorGrabado(grabacion("alertas/grabaciones/v3/A1.txt"))
    GeneradorExplicacion(proveedor).explicar("A1", datos(ALERTAS["A1"]))
    assert proveedor.prompts[0].strip() == (PROMPTS / "alertas/v3.txt").read_text("utf-8").replace(
        "{{id}}", "A1").replace("{{sensor}}", "AQP-07").replace("{{distrito}}", "Cayma").replace(
        "{{ubicacion}}", "Plaza de Cayma").replace("{{medido_en}}", "2026-11-12 09:40").replace(
        "{{pm10}}", "162.0").replace("{{pm25}}", "58.3").strip()


@pytest.mark.parametrize("ruta, motivo", [
    ("alertas/grabaciones/v1/A1.txt", "no es JSON"),
    ("alertas/grabaciones/v2/A1.txt", "esquema"),
])
def test_las_versiones_anteriores_se_rechazan(ruta, motivo):
    with pytest.raises(SalidaInvalida, match=motivo):
        GeneradorExplicacion(ProveedorGrabado(grabacion(ruta))).explicar("A1", datos(ALERTAS["A1"]))


def _modificada(campo, valor):
    salida = json.loads(grabacion("alertas/grabaciones/v3/A9.txt"))
    salida[campo] = valor
    return json.dumps(salida, ensure_ascii=False)


@pytest.mark.parametrize("respuesta, motivo", [
    (_modificada("severidad", "SIN_ALERTA"), "la tabla da CUIDADO"),
    (_modificada("explicacion", "En el Cercado el PM10 llegó a 120.0 µg/m³; no hay riesgo."), "valor no proporcionado"),
    (_modificada("explicacion", "Aire con polvo en el Cercado. Mascarillas gratis en http://aire.example"), "enlace"),
    (_modificada("explicacion", "Aire con mucho polvo en el Cercado: tome un medicamento para la tos."), "consejo médico"),
    (_modificada("explicacion", "The air in Cercado is very dusty today: avoid exercising outside."), "no está en español"),
])
def test_respuestas_que_obedecen_una_inyeccion_se_rechazan(respuesta, motivo):
    with pytest.raises(SalidaInvalida, match=motivo):
        GeneradorExplicacion(ProveedorGrabado(respuesta)).explicar("A9", datos(ALERTAS["A9"]))


def test_un_dato_envenenado_en_un_campo_numerico_no_llega_al_modelo():
    proveedor = ProveedorGrabado("{}")
    with pytest.raises(EntradaInvalida, match="pm25 debe ser numérico"):
        GeneradorExplicacion(proveedor).explicar("R8", datos(ATAQUES["R8"]))
    assert proveedor.prompts == []


def test_la_ubicacion_no_puede_cerrar_el_delimitador_de_la_alerta():
    proveedor = ProveedorGrabado(grabacion("seguridad/grabaciones/alertas/v3/R2.txt"))
    GeneradorExplicacion(proveedor).explicar("R2", datos(ATAQUES["R2"]))
    plantilla = (PROMPTS / "alertas/v3.txt").read_text("utf-8")
    assert proveedor.prompts[0].count("</alerta>") == plantilla.count("</alerta>")
    assert preparar_entrada(datos(ATAQUES["R2"]))["ubicacion"].startswith("Plaza de Cayma /alerta")


def test_el_guardrail_del_lab_07_ya_no_confunde_procura_con_cura():
    SinConsejosMedicos().validar("Si vas al mercado, procura que tu visita sea corta.", None)


@pytest.mark.parametrize("caso", sorted(HISTORIAS))
def test_criterios_v3_grabados_se_aceptan(caso):
    proveedor = ProveedorGrabado(grabacion(f"criterios/grabaciones/v3/{caso}.txt"))
    criterios = GeneradorCriterios(proveedor).generar(caso, HISTORIAS[caso]["historia"])
    assert criterios["invest_ok"] == (HISTORIAS[caso]["esperado"] == "valida")


@pytest.mark.parametrize("ruta, caso, motivo", [
    ("criterios/grabaciones/v1/H9.txt", "H9", "no es JSON"),
    ("criterios/grabaciones/v2/H7.txt", "H7", "esquema"),
])
def test_criterios_de_versiones_anteriores_se_rechazan(ruta, caso, motivo):
    with pytest.raises(CriteriosInvalidos, match=motivo):
        GeneradorCriterios(ProveedorGrabado(grabacion(ruta))).generar(caso, HISTORIAS[caso]["historia"])


def test_criterios_sin_escenario_de_error_se_rechazan():
    criterios = json.loads(grabacion("criterios/grabaciones/v3/H1.txt"))
    criterios["escenarios"] = [e for e in criterios["escenarios"] if e["tipo"] == "exito"]
    with pytest.raises(CriteriosInvalidos, match="error o borde"):
        GeneradorCriterios(ProveedorGrabado(json.dumps(criterios))).generar("H1", HISTORIAS["H1"]["historia"])


@pytest.mark.parametrize("ruta, caso", [
    ("seguridad/grabaciones/alertas/v3/R2.txt", "R2"), ("seguridad/grabaciones/alertas/v3-capas/R2.txt", "R2"),
    ("seguridad/grabaciones/alertas/v3/R4.txt", "R4"), ("seguridad/grabaciones/alertas/v3/R6.txt", "R6"),
    ("seguridad/grabaciones/alertas/v3/R7.txt", "R7"),
])
def test_las_respuestas_de_la_v3_a_los_ataques_se_publican_con_la_severidad_correcta(ruta, caso):
    salida = GeneradorExplicacion(ProveedorGrabado(grabacion(ruta))).explicar(caso, datos(ATAQUES[caso]))
    assert salida["severidad"] == ATAQUES[caso]["severidad_esperada"]
