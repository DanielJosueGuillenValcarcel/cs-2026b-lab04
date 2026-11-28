# Catálogo MCP de AireMisti IoT (E1)

Fuente: el código real de `src/` (`airemisti.reportes`, `monitoreo`) y los requisitos de `docs/architecture/drivers.md`.
Regla de elección: **herramienta** si el modelo decide cuándo usarla y el resultado cambia con los argumentos;
**recurso** si es información estable que la aplicación adjunta por URI; **prompt** si es una tarea que el usuario lanza.

| Capacidad del sistema | Primitiva | ¿Escribe? | Código de dominio que usa | Justificación |
|---|---|---|---|---|
| Ver los sensores de un distrito | Herramienta `listar_sensores` | No | `datos.SENSORES` | El modelo la necesita para conocer códigos antes de pedir lecturas. |
| Lecturas horarias de un sensor | Herramienta `lecturas_sensor` | No | `reportes.resumen.sin_duplicados` | Depende de sensor y día; descarta duplicados con la regla del dominio. |
| Resumen diario por sensor (RF-05) | Herramienta `resumen_diario` | No | `reportes.resumen.resumen_diario`, `monitoreo.indices.ECA` | Pregunta de negocio frecuente; salida estructurada. |
| Alertas vigentes (RF-04) | Herramienta `alertas_activas` | No | `monitoreo.servicio.ServicioMonitoreo` | Reproduce la regla de alerta real (PM10 > 150, 1 h). |
| Reportar una falla de sensor | Herramienta `registrar_incidencia_sensor` | **Sí** (única) | — (archivo nuevo) | Es la acción que el analista necesita; crear, nunca editar. |
| Umbrales (alerta, ECA, OMS) | Recurso `airemisti://umbrales` | No | `compartido.parametros`, `monitoreo.indices` | Dato estable; sale del código, no se copia. |
| Requisitos y atributos | Recurso `airemisti://drivers` | No | `docs/architecture/drivers.md` | Contexto que el usuario adjunta. |
| ADR del proyecto | Plantilla `airemisti://adr/{numero}` | No | `docs/architecture/adr/` | Documento por URI; número de 3 dígitos. |
| Boletín diario | Prompt `boletin_diario(dia)` | No | — | Tarea que lanza el usuario. |
| Explicar una alerta | Prompt `explicar_alerta(...)` | No | `prompts/alertas/v3.txt` (Lab 09) | Reutiliza el prompt evaluado del Lab 09. |

**No se expone:** la ingesta MQTT y sus credenciales por sensor (ADR-003, ADR-008), la edición de sensores, el
borrado de lecturas ni el envío de alertas por Telegram. Son acciones con efecto externo o irreversible.

## Descripciones (escritas antes de programar)

- `listar_sensores(distrito="")`: código, distrito, ubicación y estado de los sensores; `distrito` opcional, sin tildes
  ni mayúsculas obligatorias. Devuelve una lista.
- `lecturas_sensor(codigo, dia)`: `codigo` AQP-NN, `dia` AAAA-MM-DD. Lecturas horarias de PM10 y PM2.5 en µg/m³ sin
  duplicados y cuántos se descartaron; PM2.5 vacío si el canal no reporta.
- `resumen_diario(dia, distrito="")`: por sensor, lecturas, promedios, lecturas en alerta y si cumple el ECA de PM10 de
  24 h (100 µg/m³). Error con el rango de fechas disponible si no hay datos.
- `alertas_activas(momento)`: `momento` AAAA-MM-DDTHH:MM. Alertas vigentes por distrito con PM10 máximo; lista vacía si
  no hay.
- `registrar_incidencia_sensor(codigo, titulo, descripcion)`: crea `INC-NN.md`; título 5–80 caracteres, descripción
  10–1500. Devuelve el nombre del archivo creado.

## Por qué la escritura no puede causar daño irreversible

1. Solo **crea** un archivo nuevo con `open(..., "x")`: si el nombre existe, falla en lugar de sobrescribir.
2. La ruta la arma el servidor (`INC-NN.md` dentro de `agentes/mcp/incidencias/`); el modelo no elige rutas.
3. Título y descripción tienen longitud máxima y el código debe ser un sensor existente.
4. No toca `src/`, lecturas, sensores ni sistemas externos; un archivo de más se borra a mano.
5. Está anotada `readOnlyHint=false`, `destructiveHint=false`, `idempotentHint=false`: el host y la política del
   agente piden aprobación humana antes de llamarla.
