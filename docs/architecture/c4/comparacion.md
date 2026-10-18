# Comparaciones — Laboratorio 06

## 1. Vista dinámica C4 frente a la secuencia UML (E4)

| | [Secuencia UML del Lab 05](../../design/secuencia-ingesta-alerta.puml) | [Vista dinámica C4](img/structurizr-IngestaYAlerta.png) |
|---|---|---|
| Participantes | 12 objetos y clases (`ServicioIngesta`, `Sensor`, `Lectura`, repositorios…) | 6 contenedores y 2 elementos externos |
| Pasos | 33 mensajes con retornos | 8 pasos numerados |
| Lógica | `alt`, `loop`, `opt`, mensaje asíncrono, operaciones con parámetros | Solo el camino feliz, con el protocolo de cada paso |

La secuencia UML muestra lo que la vista dinámica omite: las operaciones de cada clase con sus parámetros, el `loop` por cada lectura del lote, la validación (`esValida`, `superaUmbral`), el camino alternativo del sensor dado de BAJA, los cambios de estado del `Sensor` y los valores de retorno. La vista dinámica, en cambio, muestra qué contenedor habla con cuál y por qué protocolo (MQTT, SQL, Redis, HTTPS), algo que la secuencia no indica. La secuencia sirve a los developers que implementan el módulo; la vista dinámica, al equipo técnico y a operaciones, para entender el recorrido de una lectura entre procesos y servidores.

## 2. Contexto escrito a mano frente a modelo exportado (E6)

| Criterio | [contexto-manual.puml](contexto-manual.puml) (C4-PlantUML a mano) | [Vista exportada de workspace.dsl](img/structurizr-Contexto.png) |
|---|---|---|
| Tiempo invertido | ≈ 10 min: 17 líneas, se escribe y se ve de inmediato | ≈ 15 min para el nivel 1, pero las 5 vistas salen del mismo modelo; cada vista nueva solo cuesta unas líneas en `views` |
| Errores encontrados | Ninguna herramienta los detecta: un alias mal escrito en `Rel` simplemente no dibuja la flecha o crea una caja nueva | `structurizr validate` rechaza identificadores inexistentes con el número de línea (se probó con `airemisti.app.noexiste`) |
| Coherencia | Las descripciones ya difieren del modelo: la del ciudadano y la del sistema son más cortas, y el sensor se marca con `System_Ext` en lugar de una etiqueta | Mismo texto en todas las vistas; los sistemas externos se distinguen con la etiqueta `Externo` y un estilo |
| Si mañana cambia el nombre de un contenedor (p. ej., "Monolito Django" → "Aplicación AireMisti") | Habría que buscarlo y cambiarlo a mano en cada `.puml` donde aparezca, con riesgo de dejar alguno desactualizado | Se cambia una sola línea en `workspace.dsl` y al exportar se actualizan las vistas de contenedores, componentes, dinámica y despliegue |

**Conclusión:** escribir a mano es más rápido para un diagrama suelto o un boceto, pero con cinco vistas que comparten elementos el modelo único evita incoherencias y es la fuente que se versiona. El diagrama a mano queda como comparación y no se usa en la documentación.
