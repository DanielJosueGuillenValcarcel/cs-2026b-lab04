# Olores de código en el flujo "procesar lectura y emitir alerta" (E1)

Versión analizada: `src/monitoreo/antes/servicio.py`, escrita a partir del diagrama de
secuencia `docs/design/secuencia-ingesta-alerta.puml` del Lab 05.

Salida de radon antes del refactor (`radon-antes.txt`):

| Método | Complejidad | Rango |
|---|:---:|:---:|
| `ServicioMonitoreo.procesar` | 26 | D |
| `ServicioMonitoreo.explicar_alerta` | 8 | B |
| `Sensor.enviar_a_mantenimiento` | 3 | A |
| `Sensor.dar_de_baja` | 3 | A |
| Promedio (10 bloques) | 6,2 | B |

## Olores detectados (Prompt IA 1) y decisión

| # | Olor (dónde) | Patrón propuesto | Principio SOLID | Costo | Decisión |
|:---:|---|---|---|---|---|
| 1 | `if/elif` por marca de sensor dentro de `procesar` (AireSense JSON, Purair texto en décimas) | Adapter por marca + Factory con registro | Abierto/cerrado, inversión de dependencias | Una clase por marca y una fábrica | Aceptado (E2) |
| 2 | `if/elif` por norma ECA/OMS con los límites escritos en el método | Strategy `NormaCalidad` | Abierto/cerrado | Una clase pequeña | Aceptado (E2) |
| 3 | Validación de anomalías mezclada con el parseo | Decorator `FiltroAnomalias` sobre cualquier lector | Responsabilidad única | Un envoltorio | Aceptado (E2) |
| 4 | Condicionales sobre `sensor.estado` repartidos entre `Sensor` y `procesar`; además el estado cambia antes de leer el payload (error) | State, uno por estado del diagrama del Lab 05 | Abierto/cerrado, responsabilidad única | Cinco clases de estado | Aceptado (E3) |
| 5 | `procesar` conoce a Telegram, al mapa y al analista y los llama a mano | Observer `PublicadorEventos` | Responsabilidad única, inversión de dependencias | Indirección: el orden de los avisos depende del orden de suscripción | Aceptado (E4) |
| 6 | Bucle de reintentos con `enviado`/`intento` incrustado en el flujo | Decorator `ConReintentos` sobre el canal | Responsabilidad única | Un envoltorio | Aceptado (E4) |
| 7 | `if/elif` por proveedor de LLM y guardrails en línea en `explicar_alerta` | Adapter `ProveedorLLM` + Decorator `ConCache` + Chain de guardrails | Abierto/cerrado, segregación de interfaces | Seis clases pequeñas | Aceptado (E5) |
| 8 | "El servicio guarda lecturas en un diccionario; un Proxy con caché evitaría consultas repetidas" | Proxy de caché sobre el repositorio de lecturas | — | Una capa más sobre la persistencia | **Rechazado**: no hay consultas repetidas en este flujo y la caché ya es Redis (ADR-002). Sería un patrón sin olor. |
| 9 | "Las fábricas deberían ser únicas en todo el sistema" | Singleton para `FabricaLectores` | — | Estado global | **Rechazado**: la regla del laboratorio prohíbe Singleton; la fábrica se inyecta en el servicio (ver bitácora, entrada 2). |

## Error que revelaron las pruebas de caracterización

En la versión antes, un sensor `SIN_SENAL` pasa a `ACTIVO` antes de leer el payload. Si llega un
payload que no se puede leer, el sistema lanza error pero el sensor ya quedó como activo.
La prueba `test_payload_invalido_no_reactiva_un_sensor_sin_senal` se marcó `xfail` en la
versión antes para documentarlo; en la versión con patrones pasa porque primero lee con el
adaptador y después notifica al estado.
