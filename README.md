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
- [ADR-005: Patrones de diseño en el flujo de lecturas y alertas](docs/architecture/adr/005-patrones-de-diseno.md)

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

## Arquitectura C4 (Lab 06)
Modelo único en Structurizr DSL ([workspace.dsl](docs/architecture/c4/workspace.dsl)); las cinco vistas se exportan desde él a C4-PlantUML y Mermaid.

### Nivel 1 — Contexto del sistema
```mermaid
graph LR
  linkStyle default fill:#ffffff

  subgraph diagram ["Nivel 1 — Contexto del sistema AireMisti IoT"]
    style diagram fill:#ffffff,stroke:#ffffff

    1["<div style='font-weight: bold'>Ciudadano</div><div style='font-size: 70%; margin-top: 0px'>[Person]</div><div style='font-size: 80%; margin-top:10px'>Vecino de Arequipa que<br />consulta la calidad del aire<br />y recibe alertas.</div>"]
    style 1 fill:#08427b,stroke:#052e56,color:#ffffff
    15["<div style='font-weight: bold'>Red de sensores PM10 / PM2.5</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>40 sensores con WiFi/4G y<br />microSD que miden cada minuto<br />y guardan lecturas durante<br />los cortes.</div>"]
    style 15 fill:#999999,stroke:#6b6b6b,color:#ffffff
    16["<div style='font-weight: bold'>Telegram Bot API</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Canal público donde se<br />publican las alertas.</div>"]
    style 16 fill:#999999,stroke:#6b6b6b,color:#ffffff
    17["<div style='font-weight: bold'>OpenStreetMap</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Servicio de teselas del mapa<br />base.</div>"]
    style 17 fill:#999999,stroke:#6b6b6b,color:#ffffff
    2["<div style='font-weight: bold'>Analista municipal</div><div style='font-size: 70%; margin-top: 0px'>[Person]</div><div style='font-size: 80%; margin-top:10px'>Registra sensores, revisa<br />alertas y descarga el<br />histórico.</div>"]
    style 2 fill:#08427b,stroke:#052e56,color:#ffffff
    3["<div style='font-weight: bold'>AireMisti IoT</div><div style='font-size: 70%; margin-top: 0px'>[Software System]</div><div style='font-size: 80%; margin-top:10px'>Recibe las lecturas de 40<br />sensores, publica el mapa de<br />calidad del aire y emite<br />alertas cuando PM10 supera<br />150 µg/m³.</div>"]
    style 3 fill:#1168bd,stroke:#0b4884,color:#ffffff

    1-. "<div>Consulta el mapa de calidad<br />del aire</div><div style='font-size: 70%'></div>" .->3
    2-. "<div>Registra sensores, revisa<br />alertas y descarga el<br />histórico</div><div style='font-size: 70%'></div>" .->3
    15-. "<div>Envía lecturas de PM10 y<br />PM2.5 cada minuto</div><div style='font-size: 70%'>[MQTT/TLS]</div>" .->3
    3-. "<div>Publica alertas de<br />contaminación</div><div style='font-size: 70%'>[HTTPS/JSON]</div>" .->16
    3-. "<div>Obtiene las teselas del mapa</div><div style='font-size: 70%'>[HTTPS]</div>" .->17
    16-. "<div>Notifica las alertas del<br />canal</div><div style='font-size: 70%'></div>" .->1
  end
```

### Vistas
| Vista | Imagen | Exportado |
|---|---|---|
| Nivel 1 — Contexto | [PNG](docs/architecture/c4/img/structurizr-Contexto.png) | [.puml](docs/architecture/c4/export/structurizr-Contexto.puml) · [.mmd](docs/architecture/c4/export/structurizr-Contexto.mmd) |
| Nivel 2 — Contenedores | [PNG](docs/architecture/c4/img/structurizr-Contenedores.png) | [.puml](docs/architecture/c4/export/structurizr-Contenedores.puml) · [.mmd](docs/architecture/c4/export/structurizr-Contenedores.mmd) |
| Nivel 3 — Componentes del Monolito Django | [PNG](docs/architecture/c4/img/structurizr-Componentes.png) | [.puml](docs/architecture/c4/export/structurizr-Componentes.puml) · [.mmd](docs/architecture/c4/export/structurizr-Componentes.mmd) |
| Dinámica — Ingesta y alerta | [PNG](docs/architecture/c4/img/structurizr-IngestaYAlerta.png) | [.puml](docs/architecture/c4/export/structurizr-IngestaYAlerta.puml) · [.mmd](docs/architecture/c4/export/structurizr-IngestaYAlerta.mmd) |
| Despliegue — Producción | [PNG](docs/architecture/c4/img/structurizr-Despliegue.png) | [.puml](docs/architecture/c4/export/structurizr-Despliegue.puml) · [.mmd](docs/architecture/c4/export/structurizr-Despliegue.mmd) |

El nivel 4 (código) no se vuelve a dibujar: es el [diagrama de clases del Lab 05](docs/design/clases.puml).

### Documentos
- [Inventario de elementos](docs/architecture/c4/inventario.md)
- [Comparaciones: vista dinámica vs. secuencia UML y modelo vs. diagrama a mano](docs/architecture/c4/comparacion.md)
- [Revisión con la lista oficial de C4 y con IA](docs/architecture/c4/revision-c4.md)
- [Explicación para público no técnico](docs/architecture/c4/explicacion.md)
- [Bitácora de IA del Lab 06](docs/architecture/c4/bitacora-ia.md)

La GitHub Action valida `workspace.dsl` con Structurizr CLI en cada push que lo modifica (falla si el modelo tiene errores) y regenera las imágenes.

## Patrones de diseño (Lab 07)

Se refactorizó el flujo crítico del Lab 05, **procesar una lectura y emitir la alerta**, en `src/monitoreo/`.
La versión ingenua se conserva en `src/monitoreo/antes/servicio.py` y las mismas pruebas de caracterización
corren sobre las dos versiones. Los servicios externos (Telegram, OpenAI, Gemini) están simulados en `externos.py`.

```bash
pip install pytest radon
PYTHONPATH=src pytest tests                         # 85 passed, 1 xfailed
radon cc -s -a src/monitoreo -e "*/antes/*,*/externos.py"
```

### Olor → patrón → prueba

| Olor en la versión antes | Patrón | Archivo | Prueba que lo demuestra |
|---|---|---|---|
| `if/elif` por marca de sensor | Adapter + Factory | `sensores.py` | `test_marca_nueva_se_registra_sin_tocar_el_servicio` |
| Validación de anomalías mezclada con el parseo | Decorator `FiltroAnomalias` | `sensores.py` | `test_filtro_de_anomalias_es_configurable` |
| `if/elif` por norma ECA/OMS | Strategy `NormaCalidad` | `indices.py` | `test_norma_nueva_se_agrega_sin_tocar_el_servicio` |
| Condicionales sobre `sensor.estado` | State | `estados.py` | `test_transiciones_fuera_del_diagrama_fallan` |
| El servicio llama a mano al mapa, Telegram y analista | Observer | `eventos.py` | `test_suscriptor_nuevo_recibe_las_alertas` |
| Bucle de reintentos dentro del flujo | Decorator `ConReintentos` | `eventos.py` | `test_reintentos_no_ocultan_errores_que_no_son_de_red` |
| `if/elif` por proveedor de LLM | Adapter + Factory `ProveedorLLM` | `ia.py` | `test_ia_explica_la_alerta_con_cualquier_proveedor` |
| Prompt repetido se paga dos veces | Decorator `ConCache` | `ia.py` | `test_cache_evita_pagar_dos_veces_el_mismo_prompt` |
| Validaciones de la respuesta del LLM en línea | Chain of Responsibility | `ia.py` | `test_guardrails_bloquean_respuestas_inseguras_de_la_ia` |

Error encontrado por las pruebas: en la versión antes, un sensor `SIN_SENAL` pasaba a `ACTIVO` aunque su
payload no se pudiera leer (`test_payload_invalido_no_reactiva_un_sensor_sin_senal`, `xfail` en antes).

### Métricas (radon 6.0.1)

| | Antes | Con patrones |
|---|:---:|:---:|
| Complejidad de `procesar` | 26 (D) | 5 (A) |
| Complejidad máxima | 26 (D) | 6 (B) |
| Complejidad promedio | 6,2 (B) | 1,74 (A) |
| SLOC | 127 | 356 |
| Archivos | 1 | 6 |

![Métricas](docs/design/patrones/img/metricas.png)

Ganamos un servicio que no cambia al agregar marcas, normas, avisos o proveedores de IA; pagamos con casi el
triple de líneas y más indirección. Patrones rechazados: Singleton, Proxy, Abstract Factory y LLM como juez
(ver [metricas.md](docs/design/patrones/metricas.md) y [ADR-005](docs/architecture/adr/005-patrones-de-diseno.md)).

### Diagramas

| Adapter + Factory + Decorator | Strategy | State |
|---|---|---|
| ![](docs/design/patrones/img/adapter-factory.png) | ![](docs/design/patrones/img/strategy.png) | ![](docs/design/patrones/img/state.png) |

| Observer + Decorator | IA: Adapter + Decorator + Chain |
|---|---|
| ![](docs/design/patrones/img/observer-decorator.png) | ![](docs/design/patrones/img/ia.png) |

Colaboración en `procesar()`: [secuencia-patrones.puml](docs/design/patrones/secuencia-patrones.puml).
El diagrama de clases del Lab 05 ([clases.puml](docs/design/clases.puml)) se actualizó y se verificó con pyreverse
([verificacion-pyreverse.md](docs/design/patrones/verificacion-pyreverse.md)).

### Documentos
- [Olores detectados y decisión](docs/design/patrones/olores.md)
- [Métricas y trade-off](docs/design/patrones/metricas.md)
- [Bitácora de IA del Lab 07](docs/design/patrones/bitacora-ia.md)
- [ADR-005: patrones de diseño](docs/architecture/adr/005-patrones-de-diseno.md)

### Integración continua (reto B)
La Action [`pruebas.yml`](.github/workflows/pruebas.yml) ejecuta `pytest` en cada push y Pull Request y falla si
algún método de `src/monitoreo` (sin contar la versión antes) llega a complejidad 11 o más (`radon cc --min C`).

## Reflexión sobre el uso de la IA
La IA aceleró la exploración: en minutos generó tres alternativas, los borradores de los diagramas y de los ADR, y su papel de "abogado del diablo" nos mostró riesgos que no habíamos considerado, como la pérdida de mensajes si el broker se reinicia.
Sin embargo, mostró un sesgo hacia tecnologías de moda: recomendó Kafka para 40 sensores, cuando un cálculo simple muestra apenas 0,67 lecturas por segundo.
También inventó datos: una clase Mosquitto inexistente en la librería diagrams y que QoS 2 evita toda pérdida aunque el broker no tenga persistencia.
Aprendimos a verificar cada afirmación contra la documentación oficial, a recalcular las cifras y a contrastar toda propuesta con nuestras restricciones (R-01 a R-05).
La IA propone; las decisiones y su justificación quedaron a cargo del equipo.
