# AireMisti IoT — Laboratorio 04: Fundamentos de arquitectura de software
Construcción de Software · EPIS-UNSA · 2026-B

## Integrantes
| Nombre | Rol en el laboratorio |
|--------|-----------------------|
| Guillén Valcárcel, Daniel Josué | Diagramador (Mermaid, PlantUML, Python Diagrams) y redactor de ADR |
| Mengoa Valeriano, Brigitte Noelia | Analista de drivers y matriz de decisión, verificadora de IA |

## Caso
AireMisti IoT es una red de 40 sensores de calidad del aire (PM10 y PM2.5) instalados en Arequipa. Cada sensor envía una lectura por minuto; los ciudadanos consultan un mapa en tiempo real, el sistema emite una alerta pública cuando PM10 supera 150 µg/m³ y el analista municipal descarga el histórico.
**Atributo de calidad crítico:** ingesta y fiabilidad. No se debe perder ninguna lectura ante cortes de red de hasta 2 horas, gracias al almacenamiento local en el sensor.

## Arquitectura elegida
Monolito modular en Django con broker MQTT (4,50 en la matriz de decisión).

```mermaid
flowchart TB
    SE["Sensor PM10 / PM2.5<br/>(40 en Arequipa)"]
    CI["Ciudadano"]
    AN["Analista municipal"]
    MQ["Broker MQTT Mosquitto<br/>(QoS 1, persistente)"]
    subgraph APP["AireMisti IoT — Monolito modular (un solo despliegue Django)"]
        API["Capa de presentación: API REST + mapa web"]
        M1["Ingesta"]
        M2["Sensores"]
        M3["Lecturas e<br/>histórico"]
        M4["Alertas"]
        M5["Mapa<br/>público"]
        INF["Capa de infraestructura: repositorios, caché y adaptadores externos"]
    end
    DB[("PostgreSQL<br/>(lecturas particionadas por mes)")]
    RD[("Redis<br/>(últimas lecturas + cola)")]
    TG["Telegram Bot API<br/>(canal de alertas)"]
    OSM["OpenStreetMap<br/>(teselas del mapa)"]
    SE -- "publica cada minuto" --> MQ
    MQ -- "suscripción" --> M1
    CI & AN --> API
    API --> M2 & M3 & M5
    M1 -- "evento LecturaRecibida" --> M3
    M1 -- "evento LecturaRecibida" --> M4
    M1 & M2 & M3 & M4 & M5 --> INF
    INF --> DB
    INF --> RD
    INF --> TG
    M5 -.-> OSM
    classDef mod fill:#E8F5E9,stroke:#2E7D32,color:#000
    classDef ext fill:#F2F2F2,stroke:#7F7F7F,color:#000,stroke-dasharray: 4 3
    classDef usr fill:#FDEDEC,stroke:#C8310E,color:#000
    class M1,M2,M3,M4,M5 mod
    class TG,OSM ext
    class SE,CI,AN usr
```

## Documentación
- [Drivers y escenarios de calidad](docs/architecture/drivers.md)
- [Matriz de decisión](docs/architecture/matriz-decision.md)
- [Bitácora de uso de IA](docs/architecture/bitacora-ia.md)
- Alternativa descartada: [alternativa.puml](docs/architecture/diagramas/alternativa.puml)
- Vista de despliegue: [despliegue.py](docs/architecture/diagramas/despliegue.py)

## Decisiones arquitectónicas
- [ADR-001: Estilo arquitectónico — monolito modular con broker MQTT](docs/architecture/adr/001-estilo-arquitectonico.md)
- [ADR-002: Almacenamiento de lecturas en PostgreSQL particionado](docs/architecture/adr/002-almacenamiento-lecturas.md)
- [ADR-003: Ingesta por MQTT con QoS 1 y credenciales por sensor](docs/architecture/adr/003-protocolo-ingesta.md)

## Diseño UML (Lab 05)
Diseño detallado de la historia crítica [HU-03: ingesta de una lectura y emisión de alerta](docs/design/historia.md), coherente con el ADR-001.

### Máquina de estados del Sensor
```mermaid
stateDiagram-v2
    [*] --> ACTIVO : darDeAlta() [credenciales MQTT emitidas]
    ACTIVO --> SIN_SENAL : marcarSinSenal() [sin lecturas por más de 10 min]
    SIN_SENAL --> ACTIVO : registrarLectura() [lote de una sola lectura]
    SIN_SENAL --> SINCRONIZANDO : iniciarSincronizacion() [lote con backlog]
    SINCRONIZANDO --> ACTIVO : completarSincronizacion() [backlog guardado]
    ACTIVO --> MANTENIMIENTO : enviarAMantenimiento()
    SIN_SENAL --> MANTENIMIENTO : enviarAMantenimiento() [sin señal por más de 24 h]
    MANTENIMIENTO --> ACTIVO : reactivar() [calibración vigente]
    MANTENIMIENTO --> BAJA : darDeBaja()
    SIN_SENAL --> BAJA : darDeBaja()
    BAJA --> [*]
    note right of SIN_SENAL
        Una tarea programada (Celery beat)
        revisa ultimaLecturaEn cada minuto
        y avisa al analista (RF-07)
    end note
```

### Diagramas
| Diagrama | Código | Imagen |
|---|---|---|
| Clases (E1) | [clases.puml](docs/design/clases.puml) | [PNG](docs/design/img/clases.png) |
| Secuencia (E2) | [secuencia-ingesta-alerta.puml](docs/design/secuencia-ingesta-alerta.puml) | [PNG](docs/design/img/secuencia-ingesta-alerta.png) |
| Estados (E3) | [estados-sensor.mmd](docs/design/estados-sensor.mmd) | [PNG](docs/design/img/estados-sensor.png) |
| Actividades (E4) | [actividades-emitir-alerta.puml](docs/design/actividades-emitir-alerta.puml) | [PNG](docs/design/img/actividades-emitir-alerta.png) |
| Paquetes (E5) | [paquetes.puml](docs/design/paquetes.puml) | [PNG](docs/design/img/paquetes.png) |
| Ingeniería inversa (E6) | [classes_airemisti.puml](docs/design/classes_airemisti.puml) | [PNG](docs/design/img/classes_airemisti.png) |

### Documentos
- [Round-trip diagrama ↔ código](docs/design/round-trip.md) y esqueleto en [`src/airemisti/`](src/airemisti)
- [Revisión de consistencia C1–C5](docs/design/consistencia.md)
- [Bitácora de IA del Lab 05](docs/design/bitacora-ia.md)

Pruebas: `PYTHONPATH=src pytest tests` (criterios de HU-03 y una prueba por transición del Sensor).

## Reflexión sobre el uso de la IA
La IA aceleró la exploración: en minutos generó tres alternativas, los borradores de los diagramas y de los ADR, y su papel de "abogado del diablo" nos mostró riesgos que no habíamos considerado, como la pérdida de mensajes si el broker se reinicia.
Sin embargo, mostró un sesgo hacia tecnologías de moda: recomendó Kafka para 40 sensores, cuando un cálculo simple muestra apenas 0,67 lecturas por segundo.
También inventó datos: una clase Mosquitto inexistente en la librería diagrams y que QoS 2 evita toda pérdida aunque el broker no tenga persistencia.
Aprendimos a verificar cada afirmación contra la documentación oficial, a recalcular las cifras y a contrastar toda propuesta con nuestras restricciones (R-01 a R-05).
La IA propone; las decisiones y su justificación quedaron a cargo del equipo.
