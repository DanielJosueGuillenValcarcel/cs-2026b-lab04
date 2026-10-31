# ADR-006: Publicar solo las alertas de lecturas frescas, con cola prioritaria, en lugar de escalar workers

- Estado: Aceptado
- Fecha: 2026-10-30
- Decisores: Daniel Josué Guillén Valcárcel y Brigitte Noelia Mengoa Valeriano

## Contexto
La red crece de 40 a 400 sensores y la alerta pública debe salir en ≤ 60 s (QA-02) incluso cuando los 400 sensores reconectan tras un corte de 2 h y reenvían 48 000 lecturas (QA-05). El canal de Telegram acepta unos 20 mensajes por minuto. La simulación de la [iteración 1](../add/iteracion-1.md) mostró que con el diseño del Lab 05 los picos antiguos del backlog generan alertas que ocupan el canal: el p95 de la alerta en vivo es de 61 s (95 s en la peor corrida). Además, `Alerta.extender` acortaba la vigencia con lecturas antiguas, por lo que el backlog republicaba la misma alerta.

## Alternativas consideradas
1. Microservicios con Kafka o un clúster EMQX: el broker medido acepta 4700–5300 mensajes/s y la red genera 6,7/s; viola R-01 a R-03 sin atacar el cuello de botella.
2. Escalar de 2 a 8 workers de Celery: en la simulación da exactamente el mismo p95, porque el límite está en el canal.
3. Corregir la vigencia y separar los picos frescos (≤ 10 min) de los antiguos con dos colas: `alertas` (pública, worker dedicado) e `historico` (aviso al analista).

## Decisión
Se adopta la alternativa 3. `ServicioIngesta` envía a `encolar_alerta` solo los picos frescos (o los mensajes de una sola lectura, que son en vivo aunque el reloj del sensor esté atrasado) y a `encolar_historico` los del backlog. `Alerta.extender` ya no acorta la vigencia. Se mantiene el monolito modular del ADR-001.

## Consecuencias
- Positivas: p95 de 1,0 s y peor corrida de 7 s (frente a 60 s); 8,7 mensajes al canal en lugar de 47,5; la ciudadanía no recibe alertas de hace dos horas; no se agrega infraestructura. FF-05 y FF-06 lo verifican en cada Pull Request.
- Negativas / riesgos: un pico ocurrido durante el corte ya no se publica, solo lo ve el analista (trade-off aceptado). Si el episodio sigue en vivo en los 29 distritos a la vez, el canal vuelve a ser el límite (63 s; riesgo R2). Se planea agrupar varias alertas en un solo mensaje si la cola del canal supera 10 mensajes.
