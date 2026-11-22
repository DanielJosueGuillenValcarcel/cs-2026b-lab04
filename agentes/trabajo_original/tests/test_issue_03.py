from datetime import date, datetime
from decimal import Decimal

from airemisti.reportes.resumen import Medicion, resumen_diario

DIA = date(2026, 11, 12)


def test_issue_03_el_promedio_de_pm25_ignora_los_valores_nulos():
    ms = [Medicion("AQP-18", datetime(2026, 11, 12, 8, 50), Decimal("180"), None),
          Medicion("AQP-18", datetime(2026, 11, 12, 9, 50), Decimal("170"), Decimal("60")),
          Medicion("AQP-18", datetime(2026, 11, 12, 10, 50), Decimal("160"), Decimal("80"))]
    r = resumen_diario(ms, DIA)["AQP-18"]
    assert r["pm10_promedio"] == Decimal("170")
    assert r["pm25_promedio"] == Decimal("70")


def test_issue_03_sin_ningun_pm25_el_promedio_queda_vacio():
    ms = [Medicion("AQP-18", datetime(2026, 11, 12, 8, 50), Decimal("180"), None)]
    assert resumen_diario(ms, DIA)["AQP-18"]["pm25_promedio"] is None
