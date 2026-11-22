from datetime import date, datetime
from decimal import Decimal

from airemisti.reportes.resumen import Medicion, resumen_diario, sin_duplicados

DIA = date(2026, 11, 12)
HORA = datetime(2026, 11, 12, 10, 0)


def test_issue_02_dos_sensores_que_miden_a_la_misma_hora_no_son_duplicados():
    ms = [Medicion("AQP-07", HORA, Decimal("80")), Medicion("AQP-12", HORA, Decimal("95"))]
    assert len(sin_duplicados(ms)) == 2


def test_issue_02_la_lectura_reenviada_por_el_mismo_sensor_si_es_duplicado():
    ms = [Medicion("AQP-07", HORA, Decimal("80")), Medicion("AQP-07", HORA, Decimal("80"))]
    assert len(sin_duplicados(ms)) == 1


def test_issue_02_el_resumen_incluye_a_los_dos_sensores():
    ms = [Medicion("AQP-07", HORA, Decimal("80")), Medicion("AQP-12", HORA, Decimal("95"))]
    assert set(resumen_diario(ms, DIA)) == {"AQP-07", "AQP-12"}
