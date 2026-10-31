# ADR-007: Ampliar la cola de Mosquitto y confirmar cada lote con un acuse de aplicación

- Estado: Aceptado
- Fecha: 2026-10-30
- Decisores: Daniel Josué Guillén Valcárcel y Brigitte Noelia Mengoa Valeriano

## Contexto
QA-03 exige 0 lecturas perdidas si la ingesta cae 10 min o el broker muere bruscamente, y QA-01 exige no perder ni duplicar el backlog de un corte de 2 h. Con 400 sensores, el valor por defecto de Mosquitto (1000 mensajes en cola por cliente desconectado) cubre solo 2,5 min de caída de la ingesta. En el experimento real se perdieron 3000 de 4000 lecturas. Además, el broker confirma (PUBACK) antes de guardar en disco: un `kill -9` perdió 800 de 800 lecturas en cola.

## Alternativas consideradas
1. Mantener la configuración del Lab 04: pierde en promedio 19 921 lecturas al mes (Monte Carlo).
2. Ampliar la cola y guardar en disco en cada cambio: no pierde nada en el broker, pero con 20 000 mensajes en cola el rendimiento baja de 5318 a 1595 mensajes/s.
3. Ampliar la cola, guardar cada 60 s y agregar un acuse de aplicación (`airemisti/<sensor>/ack`) que la ingesta publica después del `COMMIT`; el sensor borra de su microSD solo lo confirmado.
4. Un segundo broker o un clúster EMQX: elimina el punto único de falla, pero duplica el costo y no cabe en 1 mes.

## Decisión
Se adopta la alternativa 3: `max_queued_messages 200000` (8 h de caída de la ingesta), `autosave_interval 60` y acuse de aplicación en `ConsumidorMqtt`. El reenvío es idempotente gracias a la clave única del ADR-002.

## Consecuencias
- Positivas: 0 lecturas perdidas en los experimentos reales (caída de la ingesta y `kill -9` del broker) y en 1000 meses simulados. FF-07 a FF-10 lo verifican.
- Negativas / riesgos: un mensaje más por lote; el firmware de los sensores debe implementar el reenvío de lo no confirmado; si la microSD se llena en un corte muy largo, el sensor descarta lo más antiguo (riesgo R5). El VPS sigue siendo un punto único de falla (riesgo R1, aceptado para el MVP).
