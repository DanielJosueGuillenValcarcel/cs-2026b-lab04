# Bitácora de uso de IA — AireMisti IoT

| # | Fecha | Herramienta | Prompt (resumen) | Qué propuso la IA | Qué verificamos o corregimos | Decisión |
|---|-------|-------------|------------------|-------------------|------------------------------|----------|
| 1 | 29/09 | Claude | Prompt 1 adaptado: 3 alternativas de estilo para AireMisti con R-01, R-02 y R-03 | Capas con HTTP, monolito modular con MQTT y microservicios con Kafka; recomendó Kafka "porque la ingesta IoT en tiempo real necesita escalar" | Calculamos la carga real: 40 sensores × 1/min = 0,67 lecturas/s; peor caso 4800 lecturas tras un corte. No justifica Kafka y excede R-01, R-02 y R-03 | Rechazada |
| 2 | 29/09 | Claude | Prompt 2: abogado del diablo contra los microservicios con Kafka | 5 riesgos: operación de Kafka y Zookeeper/KRaft, costo de varios nodos, depuración distribuida, curva de aprendizaje, sobredimensionamiento | Contrastamos cada riesgo con R-01, R-02 y R-03; los usamos para puntuar la columna C de la matriz | Aceptada |
| 3 | 29/09 | Claude | Prompt 2 aplicado al monolito modular con MQTT | Riesgos: VPS como punto único de falla, pérdida de mensajes si el broker se reinicia, erosión de límites entre módulos | Aceptamos los riesgos y añadimos mitigaciones: microSD en el sensor, persistencia del broker e import-linter (ADR-001) | Aceptada |
| 4 | 30/09 | Claude | Generar el Mermaid de la arquitectura desde matriz-decision.md | Diagrama con los 5 módulos, pero sin el broker MQTT y con el sensor conectado directo a la API | Revisamos línea por línea: no coincidía con la decisión de E2; agregamos el broker, el evento LecturaRecibida y los servicios externos | Corregida |
| 5 | 30/09 | Claude | Proponer cómo guardar las lecturas | InfluxDB como base de series de tiempo | Implicaba una tecnología nueva y una segunda base; 21 M filas/año caben en PostgreSQL particionado por mes, que el equipo domina (ADR-002) | Rechazada |
| 6 | 01/10 | Gemini | Redactar borrador de ADR-003 (protocolo de ingesta) | Afirmó que con QoS 2 el broker nunca pierde mensajes aunque se reinicie | La documentación de Mosquitto indica que los mensajes pendientes solo sobreviven a un reinicio si se activa `persistence true`; QoS 1 basta si la ingesta descarta duplicados. Se corrigió el ADR | Corregida |
| 7 | 01/10 | Claude | Generar despliegue.py con Python Diagrams | Usó `from diagrams.onprem.queue import Mosquitto` | Revisamos el módulo instalado: la librería no tiene la clase Mosquitto (solo ActiveMQ, Celery, EMQX, Kafka, NATS, RabbitMQ y ZeroMQ); usamos el ícono genérico `IotMqtt` con la etiqueta Mosquitto | Corregida |

> Nunca se incluyeron datos personales ni información confidencial en los prompts.

## Anexo: prompts

### Prompt 1 — Generación de alternativas
Actúa como arquitecto de software senior con experiencia en sistemas IoT para municipalidades. Contexto: plataforma "AireMisti IoT" con 40 sensores de PM10 y PM2.5 en Arequipa que envían una lectura por minuto; los ciudadanos ven un mapa en tiempo real, se emite una alerta pública cuando PM10 supera 150 µg/m³ y el analista municipal descarga el histórico. Los sensores pueden perder la red hasta 2 horas y guardan las lecturas en una microSD. Restricciones: 2 developers con experiencia en Python (Django, FastAPI) y PostgreSQL, sin experiencia en Kafka ni Kubernetes; presupuesto bajo (un VPS); MVP en producción en 1 mes. Tarea: propón 3 alternativas de estilo arquitectónico. Para cada una indica fortalezas, debilidades, riesgos y qué atributos de calidad favorece o penaliza, en especial 0 lecturas perdidas y alertas en menos de 60 s. Formato: tabla comparativa en Markdown y, al final, tu recomendación justificada. No inventes APIs ni capacidades de servicios; si no estás seguro, indícalo.

### Prompt 2 — Crítica adversarial
Ahora actúa como "abogado del diablo". Critica duramente la alternativa que recomendaste: ¿qué supuestos no se cumplen con nuestras restricciones?, ¿qué podría fallar en producción cuando 40 sensores reconecten a la vez tras un corte?, ¿qué costo oculto tiene? Enumera los 5 riesgos más graves y, para cada uno, una táctica arquitectónica de mitigación.

### Prompt 3 — Diagrama Mermaid
Actúa como arquitecto de software. A partir de esta matriz de decisión (pegada abajo), genera un flowchart TB en Mermaid del monolito modular elegido con: actores Sensor, Ciudadano y Analista municipal; el broker MQTT; un subgraph con la API, los 5 módulos y la capa de infraestructura; PostgreSQL, Redis, Telegram y OpenStreetMap como servicios externos. Devuelve solo el código.

### Prompt 4 — Almacenamiento de lecturas
Actúa como especialista en bases de datos. Debemos guardar unos 21 millones de lecturas al año de 40 sensores, que pueden llegar duplicadas o desordenadas tras un corte de red. Propón 2 o 3 opciones de almacenamiento con sus riesgos y recomienda una para un equipo de 2 developers que domina PostgreSQL.

### Prompt 5 — Borrador de ADR-003
Redacta un ADR con la plantilla adjunta sobre el protocolo de ingesta de los sensores (MQTT o HTTP), considerando conectividad intermitente, que no se pierda ninguna lectura aunque la aplicación se reinicie y que solo publiquen sensores registrados. Cita los drivers QA-01, QA-02, QA-03, QA-04 y R-04.

### Prompt 6 — Vista de despliegue
Genera un script de Python con la librería diagrams (mingrammer) para la vista de despliegue: 40 sensores, broker MQTT Mosquitto, Nginx, Django con Gunicorn, proceso de ingesta, worker Celery, Redis, PostgreSQL, Prometheus y Grafana dentro de un VPS, y Telegram y OpenStreetMap como servicios externos. Usa Cluster y Edge(label=...). Usa solo clases que existan en la librería.

---

## Laboratorio 08 — Diseño de la arquitectura guiado por atributos de calidad

Herramienta: Claude. La IA propuso escenarios, tácticas, código de simulación y hallazgos de evaluación. Cada propuesta se verificó con una simulación, un experimento real con Mosquitto 2.0.18 o una medición en PostgreSQL 16 antes de decidir.

| # | Fecha | Prompt (resumen) | Qué propuso la IA | Qué verificamos o corregimos | Decisión |
|---|---|---|---|---|---|
| 1 | 30/10 | Prompt IA 1: escenarios de seis partes para 400 sensores | Escenarios candidatos para los cuatro atributos; calificó el mapa (QA-07) y la autenticación (QA-04) como (H,H) | La carga del mapa depende de los ciudadanos, no de los sensores; QA-04 ya está resuelto por ADR-003 | Corregida: QA-07 a (M,L) y QA-04 a (H,L) |
| 2 | 30/10 | Prompt IA 2: tácticas para QA-02 | Microservicios con un clúster EMQX y escalar a 8 workers de Celery | Broker medido: 4700–5300 mensajes/s frente a 6,7/s. Simulación: con 8 workers el p95 es idéntico (61 s); el límite es el canal de Telegram | Rechazada |
| 3 | 30/10 | Adaptar la simulación M/G/c del ejemplo al camino de la alerta | Modelo de colas de ingesta, worker y canal | Al reproducir el backlog con el código real apareció un error de dominio: `Alerta.extender` acortaba la vigencia con lecturas antiguas (8 lotes antiguos publicaron 4 alertas) | Corregida en el código, con prueba |
| 4 | 30/10 | Prompt IA 2: tácticas para QA-03 | Mantener ADR-003 (QoS 1 y `persistence true`) como suficiente y, como refuerzo, guardar en disco en cada cambio | Experimento real: con la cola por defecto se perdieron 3000 de 4000 lecturas; guardar en cada cambio baja el rendimiento de 5318 a 1595 mensajes/s | Corregida: cola de 200 000, autosave de 60 s y acuse de aplicación |
| 5 | 30/10 | Script del experimento con Mosquitto | Cliente de ingesta que asignaba `on_message` después de conectarse | Las primeras corridas "perdían" 1 a 3 lecturas: el broker las entregaba antes de que existiera el manejador y paho las confirmaba igual. Era un error del script, no del broker | Corregida: el manejador se asigna antes de conectar; 0 pérdidas en 5 corridas |
| 6 | 30/10 | Prompt IA 3: evaluador ATAM escéptico | 3 sensibilidades, 3 trade-offs, 6 riesgos y la afirmación "Mosquitto no escala a 400 sensores" | Cada riesgo se verificó (ver [atam-lite.md](atam-lite.md)); R6 (reloj del sensor) era real y se mitigó en el código | Aceptada, salvo el falso positivo |
| 7 | 30/10 | Pedir la evidencia de "Mosquitto no escala" | No pudo citar ninguna medición | Factor de ~700 entre la capacidad medida y la carga | **Falso positivo** refutado |
| 8 | 30/10 | FF-08: prueba de la configuración del broker | Leer `max_queued_messages` del archivo y compararlo con 48 000 | Al borrar la línea para probar que la función falla, falló con un `KeyError` que no explicaba nada | Corregida: si falta la línea se usa el valor por defecto de Mosquitto (1000) y el mensaje dice "la cola no cubre 2 h de caída de la ingesta" |

> No se incluyeron credenciales de los sensores, contraseñas de Mosquitto ni datos del VPS en los prompts. Las contraseñas de los experimentos son de prueba y se generan en un directorio temporal.
