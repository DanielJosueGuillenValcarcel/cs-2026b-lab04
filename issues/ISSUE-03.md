# Issue #3: el promedio de PM2.5 cuenta como 0 los valores que faltan

**Reportado por:** analista municipal
**Observado:** el sensor AQP-18 no tiene canal de PM2.5 en una de sus lecturas; el resumen diario promedia ese valor faltante como 0 y muestra 46,7 µg/m³ en lugar de 70 µg/m³. Si no hay ningún PM2.5, muestra 0.
**Esperado:** los valores faltantes se ignoran en el promedio; si no hay ninguno, el promedio queda vacío (`None`), no 0.
**Prueba que reproduce el error:** `tests/test_issue_03.py`
