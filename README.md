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

## Reflexión sobre el uso de la IA
La IA aceleró la exploración: en minutos generó tres alternativas, los borradores de los diagramas y de los ADR, y su papel de "abogado del diablo" nos mostró riesgos que no habíamos considerado, como la pérdida de mensajes si el broker se reinicia.
Sin embargo, mostró un sesgo hacia tecnologías de moda: recomendó Kafka para 40 sensores, cuando un cálculo simple muestra apenas 0,67 lecturas por segundo.
También inventó datos: una clase Mosquitto inexistente en la librería diagrams y que QoS 2 evita toda pérdida aunque el broker no tenga persistencia.
Aprendimos a verificar cada afirmación contra la documentación oficial, a recalcular las cifras y a contrastar toda propuesta con nuestras restricciones (R-01 a R-05).
La IA propone; las decisiones y su justificación quedaron a cargo del equipo.
