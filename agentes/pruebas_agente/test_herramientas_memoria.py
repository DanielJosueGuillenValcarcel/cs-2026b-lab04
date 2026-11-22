import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from agente.herramientas import Herramientas

MODULO = '''"""Reportes."""


class Medicion:
    """Una lectura del histórico."""

    def es_valida(self, umbral):
        """Indica si la lectura es usable."""
        return True


def promedio(valores):
    """Promedio sin nulos."""
    return None
'''


def test_mapa_repo_lista_clases_metodos_y_funciones_con_linea_y_docstring(tmp_path):
    (tmp_path / "reportes").mkdir()
    (tmp_path / "reportes" / "resumen.py").write_text(MODULO, encoding="utf-8")
    (tmp_path / "reportes" / "__init__.py").write_text('"""Vacío."""\n', encoding="utf-8")
    mapa = Herramientas(tmp_path).mapa_repo("reportes").splitlines()
    assert mapa[0] == "reportes/resumen.py:"
    assert mapa[1] == "  class Medicion  # Una lectura del histórico."
    assert mapa[2] == "      def es_valida(self, umbral) [línea 7]  # Indica si la lectura es usable."
    assert mapa[3] == "  def promedio(valores) [línea 12]  # Promedio sin nulos."
    assert len(mapa) == 4


def test_mapa_repo_ignora_pycache_y_no_sale_del_sandbox(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.py").write_text("def oculto():\n    pass\n", encoding="utf-8")
    h = Herramientas(tmp_path)
    assert h.mapa_repo() == "(sin archivos .py)"
    try:
        h.mapa_repo("../..")
        assert False
    except PermissionError:
        pass


def test_notas_se_acumulan_en_notas_md(tmp_path):
    h = Herramientas(tmp_path)
    assert h.leer_notas() == "(sin notas)"
    assert h.anotar("hipótesis: promedio cuenta None como 0") == "OK: 1 nota(s) en notas.md"
    assert h.anotar("  revisado: airemisti/reportes/resumen.py  ") == "OK: 2 nota(s) en notas.md"
    assert h.leer_notas() == "- hipótesis: promedio cuenta None como 0\n- revisado: airemisti/reportes/resumen.py"
    assert (tmp_path / "notas.md").exists()


def test_catalogo_documenta_las_herramientas_nuevas(tmp_path):
    c = Herramientas(tmp_path).catalogo()
    for nombre in ("mapa_repo", "anotar", "leer_notas"):
        assert nombre in c and c[nombre].startswith(nombre + "(")
