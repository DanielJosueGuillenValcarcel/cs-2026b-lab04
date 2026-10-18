# Revisión de las vistas C4 — AireMisti IoT

## 1. Lista de revisión oficial (c4model.com/diagrams/checklist)

Vistas: **Ctx** = contexto, **Cont** = contenedores, **Comp** = componentes, **Din** = dinámica, **Desp** = despliegue (ver [img/](img)).

| Grupo | Pregunta | Ctx | Cont | Comp | Din | Desp | Evidencia |
|---|---|---|---|---|---|---|---|
| General | ¿Tiene título? | Sí | Sí | Sí | Sí | Sí | Cada vista tiene `title` en `workspace.dsl` ("Nivel 1 — Contexto…", etc.) |
| General | ¿Se entiende el tipo de diagrama y su alcance? | Sí | Sí | Sí | Sí | Sí | El título nombra el nivel o la vista, y el borde indica el sistema o contenedor |
| General | ¿Tiene leyenda? | Sí | Sí | Sí | Sí | Sí | `SHOW_LEGEND` del exportador; los íconos de la leyenda se ven como recuadros (ver H4) |
| Elementos | ¿Cada elemento tiene nombre? | Sí | Sí | Sí | Sí | Sí | — |
| Elementos | ¿Se entiende el tipo de cada elemento? | Sí | Sí | Sí | Sí | Sí | Forma y color por tipo (persona, cilindro para datos, tubo para el broker) y leyenda |
| Elementos | ¿Cada elemento tiene descripción? | Sí | Sí | Sí | Sí | Sí | Todas las descripciones están en el modelo |
| Elementos | ¿Se indica la tecnología cuando corresponde? | No aplica | Sí | Sí | Sí | Sí | El nivel 1 no muestra tecnologías internas (correcto); contenedores y componentes sí |
| Elementos | ¿Se entienden colores, formas y bordes? | Sí | Sí | Sí | Sí | Sí | Gris = externo; azul oscuro = persona; azul = sistema o contenedor; celeste = componente |
| Relaciones | ¿Cada flecha tiene una etiqueta con su intención? | Sí | Sí | Sí | Sí | Sí | Verbos como "Publica alertas", "Consume tareas"; ninguna dice solo "usa" |
| Relaciones | ¿La etiqueta coincide con la dirección? | Sí | Sí | Sí | Sí (tras corregir H5) | Sí | — |
| Relaciones | ¿Se indica la tecnología o el protocolo? | Sí, salvo las personas | Sí | Sí, salvo las llamadas internas (ver H6) | Sí | Sí | MQTT/TLS, HTTPS/JSON, SQL/TCP, Redis protocol |
| Relaciones | ¿Se entienden los estilos de línea y puntas? | Sí | Sí | Sí | Sí | Sí | Una sola clase de línea con punta en el destino |

## 2. Hallazgos de la IA (Prompt IA 2) y verificación del equipo

```text
Actúa como revisor de diagramas de arquitectura. Evalúa estas vistas exportadas de un modelo C4 [5 archivos .puml de export/] con la lista de revisión de c4model.com: generales, elementos y relaciones. Responde en una tabla (vista, pregunta de la lista, cumple sí/no, evidencia, corrección sugerida). No inventes problemas: si algo cumple, indícalo.
```

| # | Vista | Hallazgo de la IA | Verificación del equipo | Decisión |
|---|---|---|---|---|
| H1 | Despliegue | Nginx y Prometheus + Grafana aparecen sin ninguna relación; no se entiende qué hacen en el diagrama. | **Correcto.** Eran nodos de infraestructura sueltos. | **Corregido:** se agregaron "Reenvía las peticiones HTTPS" (Nginx → Monolito) y "Recoge métricas" (Prometheus → Monolito). |
| H2 | Componentes | Ingesta se ejecuta como proceso aparte, así que debería ser un contenedor y no un componente del Monolito Django. | **Correcto a medias.** Corre en otro proceso, pero comparte código, base de datos y despliegue con el resto de módulos (ADR-001) y coincide con `paquetes.puml`. | **Se mantiene** como componente; su descripción indica que corre con `manage.py ingesta` y el inventario documenta la decisión. |
| H3 | Contenedores | El Broker MQTT es infraestructura, igual que Nginx, y no debería modelarse como contenedor. | **Falso positivo.** Mosquitto guarda los mensajes de forma persistente y de él depende que no se pierdan lecturas (ADR-003, QA-01, QA-03). En C4 un broker o una cola que guarda datos es un contenedor, como Redis o PostgreSQL. | Sin cambios. |
| H4 | Todas | La leyenda muestra un recuadro vacío delante de cada tipo de elemento. | **Correcto.** Es el ícono del tipo, que no se dibuja con la fuente del renderizador; la leyenda igual se lee por color y texto. | **Documentado.** |
| H5 | Dinámica | En el paso 2 la etiqueta "Recibe el mensaje por su suscripción" no coincide con la flecha, que va del Monolito al broker. | **Correcto.** La flecha indica quién inicia la comunicación (el suscriptor), pero el verbo describía lo contrario. | **Corregido:** "Consume la lectura de su suscripción". |
| H6 | Componentes | Las relaciones entre componentes no indican tecnología. | **Falso positivo.** Son llamadas dentro del mismo proceso de Python (servicios de aplicación, ADR-001); la lista pide la tecnología "si corresponde" y aquí no hay protocolo de red. Las relaciones que salen del contenedor sí la indican. | Sin cambios. |

**Resumen:** 6 hallazgos; 2 corregidos (H1, H5), 1 mantenido con justificación (H2), 1 documentado (H4) y 2 falsos positivos (H3, H6).
