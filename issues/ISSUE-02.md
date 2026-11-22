# Issue #2: se pierden lecturas de sensores distintos que miden a la misma hora

**Reportado por:** analista municipal
**Observado:** el resumen del 12/11/2026 solo muestra el sensor AQP-07; la lectura de AQP-12 de las 10:00 desapareció porque AQP-07 midió a la misma hora.
**Esperado:** solo es duplicado la lectura que el **mismo sensor** reenvía con la misma hora (RF-02, QA-01: 0 lecturas perdidas, 0 duplicadas). Dos sensores distintos a la misma hora son dos lecturas.
**Prueba que reproduce el error:** `tests/test_issue_02.py`
