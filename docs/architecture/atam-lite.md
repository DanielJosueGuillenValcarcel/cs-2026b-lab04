# Evaluación ATAM-lite — AireMisti IoT con 400 sensores (E3 y E7)

**Material evaluado:** [árbol de utilidad](utilidad/escenarios.md), [iteración 1 de ADD](add/iteracion-1.md) y la simulación de [fitness/alertas.py](../../fitness/alertas.py). Esta primera evaluación se completa en el commit E7 con las iteraciones 2 y 3.

**Método:** se usó el Prompt IA 3 con la IA en el rol de **evaluador ATAM escéptico**. El equipo verificó cada hallazgo contra la evidencia: se aceptó, se mitigó o se refutó con datos.

> Actúa como evaluador ATAM escéptico. Te paso el árbol de utilidad, la iteración 1 y los resultados de la simulación [pegar]. Para cada escenario (H,*) identifica puntos de sensibilidad, puntos de trade-off, riesgos y no riesgos. Para cada riesgo indica probabilidad e impacto (1 a 5) y una pregunta incómoda. No propongas rediseños completos; cita la evidencia que te falta.

## Puntos de sensibilidad
| ID | Hallazgo | Evidencia | Respuesta del equipo |
|---|---|---|---|
| S1 | El p95 de la alerta en vivo depende de cuántas alertas compiten por el canal de Telegram (20 mensajes/min). | Curva de la iteración 1: con el diseño anterior, más de 60 s desde 12 distritos con picos antiguos. | **Aceptado.** Por eso los picos antiguos no se publican (iteración 1); queda el caso de 29 distritos en vivo (R2). |
| S3 | La clasificación por frescura depende del reloj del sensor. | Sin evidencia previa: es una pregunta del evaluador. | **Aceptado y mitigado** (ver R6). |

## Puntos de trade-off
| ID | Hallazgo | Respuesta del equipo |
|---|---|---|
| T2 | Frescura (latencia de las alertas en vivo) frente a informar a la ciudadanía de un pico ocurrido durante el corte. | **Aceptado:** ese pico ya pasó; el analista lo recibe en la cola `historico` y decide si lo comunica. |

## Riesgos
| ID | Riesgo | P | I | Pregunta incómoda del evaluador | Respuesta del equipo |
|---|---|:---:|:---:|---|---|
| R1 | Un solo VPS es punto único de falla para QA-02 y QA-03. | 2 | 5 | "¿Qué pasa si el VPS no vuelve en 3 horas?" | **Se revisa en la iteración 2.** Un segundo VPS duplica el costo (R-03). |
| R2 | Si el episodio está en vivo en los 29 distritos a la vez, el canal vuelve a ser el límite. | 2 | 4 | "¿Cuántos distritos aguanta el canal?" | **Aceptado con umbral medido:** p95 de 46 s con 20 distritos y de 63 s con 29. Mitigación planificada: agrupar alertas en un solo mensaje. |
| R3 | Redis sin AOF pierde las tareas encoladas si se reinicia. | 2 | 3 | "¿Una alerta puede desaparecer en un reinicio de Redis?" | **Aceptado:** la siguiente lectura en vivo del distrito (≤ 1 min después) vuelve a encolar la alerta. En el peor caso se retrasa 60 s y no se pierde. |
| R4 | Con 400 credenciales, una clave filtrada permite enviar datos falsos, ¿también de otros sensores? | 2 | 3 | "¿Qué impide que un sensor publique en el tema de otro?" | **Se atiende en la iteración 3** (QA-06). |
| R6 | Un sensor con el reloj atrasado más de 10 min marca sus lecturas en vivo como antiguas y su alerta no se publica. | 3 | 4 | "¿Los sensores sincronizan la hora? ¿Qué pasa si NTP falla?" | **Mitigado en el código:** un mensaje de una sola lectura siempre es en vivo, sin importar su hora (`test_lectura_en_vivo_con_reloj_atrasado_publica_la_alerta`). |

**Riesgos para las iteraciones siguientes:** R4 orienta la iteración 3 (aislamiento entre sensores) y R1 y R3 se revisan en la iteración 2 (caídas del servidor). R6 era el único en zona crítica (P × I = 12) y se mitigó en el código antes de seguir.

## No riesgos
| ID | Decisión evaluada | Evidencia |
|---|---|---|
| N1 | El monolito modular con un solo proceso de ingesta soporta la reconexión de 400 sensores. | Lote de 120 lecturas en 2,4 ms en PostgreSQL 16 con 2,88 millones de filas; backlog de 48 000 lecturas en ~2,4 s. |

## Falsos positivos de la IA refutados
| Afirmación del evaluador | Por qué se refutó |
|---|---|
| "Con más workers de Celery se resuelve la latencia de las alertas." | La simulación da el mismo p95 con 2 y con 8 workers: el límite es el canal de Telegram. |
