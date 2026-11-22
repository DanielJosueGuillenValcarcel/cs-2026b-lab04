import sys, pathlib, pytest
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from agente.contrato import validar_decision

H = {"leer_archivo", "editar_archivo", "ejecutar_pruebas", "mapa_repo"}


@pytest.mark.parametrize("d", [
    {"pensamiento": "leo el resumen", "accion": "leer_archivo", "args": "airemisti/reportes/resumen.py"},
    {"pensamiento": "listo", "final": "Issue resuelto", "confianza": 0.9},
    {"pensamiento": "leo", "accion": ["leer_archivo"], "args": {}},
    {"pensamiento": "  ", "accion": "ejecutar_pruebas", "args": {}},
    {"pensamiento": "nada que hacer", "accion": "", "args": {}},
    {"pensamiento": "termino", "final": {"estado": "resuelto"}},
    {"pensamiento": "edito", "accion": "editar_archivo", "args": {}, "ruta": "airemisti/reportes/resumen.py"},
    None,
])
def test_contrato_rechaza_decisiones_invalidas_de_airemisti(d):
    ok, motivo = validar_decision(d, H)
    assert ok is False and motivo


def test_contrato_acepta_la_herramienta_nueva_mapa_repo():
    assert validar_decision({"pensamiento": "veo la estructura", "accion": "mapa_repo", "args": {"carpeta": "airemisti"}}, H) == (True, "")
