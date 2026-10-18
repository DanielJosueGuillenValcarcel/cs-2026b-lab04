# Inventario de elementos del modelo C4 — AireMisti IoT

Cada elemento de [workspace.dsl](workspace.dsl) sale de un artefacto de los Laboratorios 04 o 05.

| Elemento | Tipo C4 | Origen |
|---|---|---|
| Ciudadano | Persona | [drivers.md](../drivers.md) (RF-03) |
| Analista municipal | Persona | [drivers.md](../drivers.md) (RF-05, RF-06, RF-07) |
| AireMisti IoT | Sistema de software | Caso N.º 3 |
| Red de sensores PM10 / PM2.5 | Sistema externo | [drivers.md](../drivers.md) (RF-01, RF-02, R-04) |
| Telegram Bot API (canal de alertas) | Sistema externo | [ADR-001](../adr/001-estilo-arquitectonico.md), [despliegue.py](../diagramas/despliegue.py) |
| OpenStreetMap (teselas del mapa) | Sistema externo | [despliegue.py](../diagramas/despliegue.py), README del Lab 04 |
| Mapa web | Contenedor (navegador) | README del Lab 04 ("API REST + mapa web") |
| Monolito Django | Contenedor | [ADR-001](../adr/001-estilo-arquitectonico.md) |
| Worker Celery | Contenedor | [despliegue.py](../diagramas/despliegue.py), [secuencia del Lab 05](../../design/secuencia-ingesta-alerta.puml) |
| Broker MQTT Mosquitto | Contenedor | [ADR-003](../adr/003-protocolo-ingesta.md) |
| PostgreSQL (lecturas particionadas por mes) | Contenedor (base de datos) | [ADR-002](../adr/002-almacenamiento-lecturas.md) |
| Redis (últimas lecturas y cola) | Contenedor (cola y caché) | [despliegue.py](../diagramas/despliegue.py) |
| Ingesta, Sensores, Lecturas e histórico, Alertas, Mapa público | Componentes del Monolito Django | [paquetes.puml](../../design/paquetes.puml) (Lab 05) |
| Flujo "ingesta de una lectura y emisión de alerta" | Vista dinámica | [secuencia-ingesta-alerta.puml](../../design/secuencia-ingesta-alerta.puml) (Lab 05) |
| VPS con Nginx, Prometheus y Grafana | Nodos de despliegue e infraestructura | [despliegue.py](../diagramas/despliegue.py), R-03 |
| Clases del dominio (nivel 4) | Código | [clases.puml](../../design/clases.puml) (Lab 05), no se vuelve a dibujar |

## Decisiones de modelado

- **Los sensores son un sistema externo.** Su firmware no se construye en el MVP (R-04); el sistema solo recibe sus lecturas por MQTT.
- **Mosquitto es un contenedor, no infraestructura**, porque es un almacén de mensajes persistente del que depende la fiabilidad de la ingesta (ADR-003), igual que PostgreSQL o Redis.
- **Nginx, Prometheus y Grafana son infraestructura.** Aparecen como nodos en la vista de despliegue y no como contenedores.
- **La ingesta es un componente del Monolito Django.** Comparte código y despliegue con el resto de módulos (ADR-001), aunque se ejecuta como un proceso aparte (`python manage.py ingesta`).
- **El módulo `compartido` no es un componente**: solo contiene la excepción `TransicionInvalida` y el parámetro `UMBRAL_PM10`, sin responsabilidad propia.
