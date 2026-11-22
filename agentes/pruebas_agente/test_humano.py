import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from agente.politica import Politica, aprobar_por_consola

EDICION = {"ruta": "airemisti/reportes/resumen.py", "antes": "int(pm10) > UMBRAL_PM10", "despues": "pm10 > UMBRAL_PM10"}


def consola(respuestas):
    pendientes, salida = list(respuestas), []
    return (lambda _: pendientes.pop(0)), salida.append, salida


def test_aprobar_por_consola_insiste_hasta_recibir_s_o_n():
    entrada, imprimir, salida = consola(["si", "", "  S  "])
    assert aprobar_por_consola(EDICION, entrada, imprimir) is True
    assert sum("Respuesta no válida" in s for s in salida) == 2
    assert "pm10 > UMBRAL_PM10" in salida[0]


def test_aprobar_por_consola_rechaza_con_n():
    entrada, imprimir, _ = consola(["n"])
    assert aprobar_por_consola(EDICION, entrada, imprimir) is False


def test_politica_bloquea_la_edicion_que_el_humano_rechaza():
    p = Politica()
    p.aprobar_edicion = lambda args: False
    v = p.evaluar("editar_archivo", EDICION, 3)
    assert not v.permitido and "rechazó" in v.motivo
    assert p.evaluar("leer_archivo", {"ruta": EDICION["ruta"]}, 4).permitido


def test_politica_no_consulta_al_humano_por_rutas_protegidas():
    llamadas = []
    p = Politica()
    p.aprobar_edicion = lambda args: llamadas.append(args) or True
    assert not p.evaluar("editar_archivo", {"ruta": "tests/test_issue_01.py", "antes": "a", "despues": "b"}, 1).permitido
    assert llamadas == []
