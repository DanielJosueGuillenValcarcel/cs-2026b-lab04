# Bitácora de uso de IA — Laboratorio 06 (Modelo C4)

| # | Fecha | Herramienta | Prompt (resumen) | Qué propuso la IA | Qué verificamos o corregimos | Decisión |
|---|---|---|---|---|---|---|
| 1 | 17/10 | Claude | Armar el inventario de elementos C4 a partir de drivers.md, los ADR, despliegue.py y paquetes.puml | Tabla de personas, sistemas, contenedores y componentes con su origen | Cada fila se buscó en su archivo de origen. Nginx, Prometheus y Grafana se pasaron de contenedores a infraestructura (vista de despliegue) | Corregida |
| 2 | 17/10 | Claude | Prompt IA 1 adaptado: borrador de `workspace.dsl` con las 5 vistas, usando solo tecnologías del ADR-001 | Modelo con 2 personas, 3 sistemas externos, 6 contenedores, 5 componentes y entorno "Producción" | Se descartó Docker Compose (el entorno del ejemplo de la guía) porque no figura en el ADR-001 ni en despliegue.py; el despliegue usa servicios systemd en el VPS. Se validó cada etapa con `structurizr validate` | Corregida |
| 3 | 17/10 | Claude | ¿La ingesta es un contenedor o un componente? | Modelarla como contenedor "Servicio de ingesta", como sugiere la Tabla 10 de la guía | Se mantuvo como componente del Monolito Django: mismo código y despliegue (ADR-001) y coincide con paquetes.puml; el proceso aparte se indica en la descripción | Rechazada con justificación |
| 4 | 17/10 | Claude | Ajustar la exportación a C4-PlantUML | Agregar `title` a cada vista y la propiedad `c4plantuml.tags` | Sin la propiedad, los sistemas externos salían azules y los títulos en inglés ("Containers"); se comprobó en las imágenes exportadas | Aceptada |
| 5 | 17/10 | Claude | Prompt IA 2: auditor C4 sobre las 5 vistas exportadas | 6 hallazgos (ver [revision-c4.md](revision-c4.md)) | H1 y H5 corregidos en el modelo; H3 (broker como infraestructura) y H6 (tecnología en llamadas internas) rechazados como falsos positivos | Corregida |
| 6 | 17/10 | Claude | Prompt IA 3: explicar el contexto a la municipalidad en 120 palabras o menos | Texto de 102 palabras sin jerga técnica | Cada afirmación se comparó con el modelo ([explicacion.md](explicacion.md)); se evitó prometer que todos los vecinos reciben la alerta | Corregida |
| 7 | 17/10 | Claude | Reto opcional: GitHub Action que valide `workspace.dsl` y regenere las imágenes | Paso con Structurizr CLI y PlantUML | Se comprobó localmente que `validate` falla con un identificador inexistente, de modo que el push falla si el modelo tiene errores | Aceptada |

> No se incluyeron credenciales de los sensores, contraseñas de Mosquitto ni direcciones del VPS en los prompts.
