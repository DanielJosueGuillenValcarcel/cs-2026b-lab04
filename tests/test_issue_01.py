from datetime import date, datetime
from decimal import Decimal

import pytest

from airemisti.reportes.resumen import Medicion, resumen_diario, supera_umbral

DIA = date(2026, 11, 12)


@pytest.mark.xfail(strict=True, reason="ISSUE-01 abierto")
def test_issue_01_un_pm10_con_decimales_sobre_el_umbral_es_alerta():
    assert supera_umbral(Decimal("150.4"))
    assert not supera_umbral(Decimal("150"))


@pytest.mark.xfail(strict=True, reason="ISSUE-01 abierto")
def test_issue_01_el_resumen_cuenta_en_alerta_la_lectura_de_150_4():
    ms = [Medicion("AQP-07", datetime(2026, 11, 12, 9, 40), Decimal("150.4")),
          Medicion("AQP-07", datetime(2026, 11, 12, 9, 41), Decimal("120"))]
    assert resumen_diario(ms, DIA)["AQP-07"]["lecturas_en_alerta"] == 1
