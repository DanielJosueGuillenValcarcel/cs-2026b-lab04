# Issue #1: el resumen diario no cuenta como alerta un PM10 de 150,4 µg/m³

**Reportado por:** analista municipal
**Observado:** el resumen del 12/11/2026 del sensor AQP-07 muestra 0 lecturas en alerta, aunque a las 09:40 midió PM10 = 150,4 µg/m³.
**Esperado:** RF-04 dice que hay alerta cuando el PM10 **supera** 150 µg/m³; 150,4 la supera y debe contarse. 150 exacto no la supera.
**Prueba que reproduce el error:** `tests/test_issue_01.py`
