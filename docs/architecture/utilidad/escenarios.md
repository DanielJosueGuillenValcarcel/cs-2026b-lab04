# Escenarios de calidad para el crecimiento a 400 sensores (E1)

**Escenario de crecimiento (caso N.º 3):** la red pasa de 40 a 400 sensores, las alertas públicas deben salir en
menos de 1 minuto y los cortes de red pueden durar hasta 2 h. Siguen vigentes las restricciones de
[drivers.md](../drivers.md): 1 mes de plazo (R-01), 2 developers con Python y PostgreSQL (R-02) y un solo VPS (R-03).

**Cifras de partida:** 400 sensores × 1 lectura/min = 6,7 lecturas/s. Si los 400 reconectan a la vez tras 2 h, llegan
400 mensajes de backlog con 48 000 lecturas. La provincia de Arequipa tiene 29 distritos, unos 14 sensores por distrito.

Los escenarios candidatos salieron del Prompt IA 1; el equipo los redujo a 9 y corrigió dos calificaciones.

| ID | Atributo | Fuente | Estímulo | Entorno | Artefacto | Respuesta | Medida | (I, D) |
|---|---|---|---|---|---|---|---|:---:|
| QA-02 | Rendimiento | Sensor | Lectura en vivo con PM10 > 150 µg/m³ | 400 sensores reenviando su backlog tras un corte | Ingesta, worker de alertas y canal de Telegram | Publica la alerta del distrito | ≤ 60 s (p95) desde la medición | (H,H) |
| QA-05 | Rendimiento | 400 sensores | Reconectan a la vez con 120 lecturas cada uno | Fin de un corte de red de 2 h | Broker e ingesta | Guarda todas las lecturas | Backlog guardado en ≤ 5 min | (H,M) |
| QA-07 | Rendimiento | Ciudadanos | 200 consultas/s al mapa | Hora punta | API del mapa (lee de Redis) | Devuelve el nivel de cada sensor | p95 ≤ 500 ms | (M,L) |
| QA-01 | Fiabilidad | Sensor | Pierde la red 2 h y reenvía 120 lecturas | Reconexión | Broker, ingesta y PostgreSQL | Acepta todas con su hora original | 0 perdidas, 0 duplicadas | (H,M) |
| QA-03 | Disponibilidad | Servidor | La ingesta cae 10 min o el broker muere con `kill -9` | Operación normal | Broker MQTT persistente | No se pierde ninguna lectura | 0 lecturas perdidas | (H,H) |
| QA-04 | Seguridad | Dispositivo externo | Intenta publicar sin credenciales | Operación normal | Broker MQTT | Rechaza la conexión | 100 % rechazadas | (H,L) |
| QA-06 | Seguridad | Sensor con credenciales robadas | Publica en el tema de otro sensor | Operación normal | Broker MQTT (ACL) | Descarta la publicación | 0 publicaciones cruzadas aceptadas | (H,M) |
| QA-08 | Modificabilidad | Analista municipal | Da de alta 50 sensores nuevos | Operación normal | Credenciales y ACL del broker | Los sensores publican | ≤ 1 h; sin reiniciar el broker ni desplegar código | (H,M) |
| QA-09 | Modificabilidad | Municipalidad | Compra una marca de sensor nueva | Desarrollo | Lectores de sensores (Lab 07) | Se integra la marca | ≤ 2 días, modificando solo un adaptador | (M,L) |

## Calificaciones corregidas por el equipo

| Escenario | Propuesta de la IA | Decisión del equipo | Justificación |
|---|---|---|---|
| QA-07 (mapa) | (H,H): "10 veces más sensores implican 10 veces más carga en el mapa" | **(M,L)** | La carga del mapa depende de cuántos ciudadanos consultan, no de cuántos sensores hay. La API lee 400 claves de Redis (una por sensor), un tamaño que no cambia el diseño. |
| QA-04 (sin credenciales) | (H,H) | **(H,L)** | Sigue siendo importante, pero ya está resuelto: ADR-003 exige usuario y contraseña por sensor y TLS, y `allow_anonymous false` no depende del número de sensores. La dificultad nueva está en el aislamiento entre sensores (QA-06). |

## Orden de las iteraciones de ADD

Los escenarios (H,H) y (H,M) definen tres iteraciones:

1. **QA-02 y QA-05:** rendimiento de las alertas durante la reconexión masiva.
2. **QA-03 y QA-01:** cero lecturas perdidas ante caídas de la ingesta o del broker.
3. **QA-06 y QA-08:** aislamiento entre sensores y altas sin reiniciar.
