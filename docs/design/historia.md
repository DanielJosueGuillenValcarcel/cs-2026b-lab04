# Historia de usuario crítica — AireMisti IoT

**HU-03:** Como analista municipal, quiero que cada lectura que publica un sensor se guarde sin pérdidas ni duplicados y que se emita una alerta pública cuando PM10 supere 150 µg/m³, para que la población se entere a tiempo de un pico de contaminación.

Drivers relacionados: RF-01, RF-02, RF-04, RF-07, QA-01, QA-02, QA-04 (ver [drivers.md](../architecture/drivers.md)).

## Criterios de aceptación

1. **Lectura normal con alerta**
   - **Dado** un sensor registrado en estado ACTIVO,
   - **cuando** publica una lectura con PM10 = 180 µg/m³,
   - **entonces** la lectura se guarda con su hora de medición, el sensor se marca en rojo en el mapa y la alerta se publica en el canal de Telegram en 60 s o menos (QA-02).

2. **Reenvío tras un corte de red**
   - **Dado** un sensor en estado SIN_SENAL que estuvo 2 horas sin red,
   - **cuando** se reconecta y reenvía sus 120 lecturas acumuladas,
   - **entonces** se guardan todas con su hora original, sin duplicados (0 perdidas, 0 duplicadas) y el sensor vuelve a ACTIVO (QA-01, ADR-002).

3. **Alerta ya vigente**
   - **Dado** una alerta vigente en el distrito,
   - **cuando** llega otra lectura con PM10 > 150 µg/m³ del mismo distrito,
   - **entonces** la alerta existente se extiende y no se publica un aviso repetido.

4. **Sensor no habilitado**
   - **Dado** un sensor dado de BAJA o no registrado,
   - **cuando** publica una lectura,
   - **entonces** la lectura se descarta, el intento queda registrado y no se genera ninguna alerta (QA-04).
