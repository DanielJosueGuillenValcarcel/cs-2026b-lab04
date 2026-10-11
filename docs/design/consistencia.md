# Revisión de consistencia C1–C5 — AireMisti IoT

## 1. Verificación del equipo (regla por regla)

| Regla | Qué se revisó | Resultado |
|---|---|---|
| C1 | Los 33 mensajes de [secuencia-ingesta-alerta.puml](secuencia-ingesta-alerta.puml) contra [clases.puml](clases.puml). Mensajes a `ConsumidorMqtt` (alRecibirMensaje), `ServicioIngesta` (procesarLote), `RepositorioSensores` (buscarPorCodigo, guardar), `Sensor` (estaHabilitado, iniciarSincronizacion, registrarLectura, completarSincronizacion), `Lectura` (create, esValida, superaUmbral), `RepositorioLecturas` (guardarLote), `ServicioAlertas` (evaluar), `RepositorioAlertas` (alertaActiva, guardar), `Alerta` (create, extender, mensaje) y `CanalAlertas` (publicar). | Cumple. El mensaje 1 (`PUBLISH`) va del dispositivo al broker externo: es un mensaje del protocolo MQTT, no una operación de una clase del sistema. |
| C2 | Las 10 transiciones de [estados-sensor.mmd](estados-sensor.mmd) contra las operaciones de `Sensor`. | Cumple: cada transición se nombra con una operación de `Sensor` y hay una prueba por transición en `tests/`. |
| C3 | Multiplicidades contra [historia.md](historia.md). | Cumple: un sensor registra 0..* lecturas; una alerta se sustenta en 1..* lecturas (código: `ValueError` si no hay lecturas); un sensor tiene exactamente 1 ubicación. |
| C4 | [paquetes.puml](paquetes.puml) contra el ADR-001 y contra `packages_airemisti.puml` (pyreverse). | Cumple: sin ciclos. `alertas` no depende de `ingesta`; `lecturas` y `sensores` solo dependen de `compartido`. |
| C5 | Nombres en historia, diagramas y código. | Cumple con la equivalencia camelCase ↔ snake_case documentada en [round-trip.md](round-trip.md). Los estados del Mermaid coinciden con `EstadoSensor`. |

## 2. Hallazgos de la IA (Prompt IA 3)

Herramienta: Claude, en una revisión aparte con el rol de auditor y sin acceso al razonamiento con el que se hicieron los diagramas. Se le pasaron los cinco archivos con este prompt:

```text
Actúa como revisor de diseño. Te paso cinco diagramas UML en PlantUML/Mermaid del módulo de ingesta y alertas de AireMisti IoT (monolito modular en Django con broker MQTT, ADR-001): clases.puml, secuencia-ingesta-alerta.puml, estados-sensor.mmd, actividades-emitir-alerta.puml y paquetes.puml.
Verifica estas reglas y responde en una tabla (regla, elemento, problema, corrección sugerida):
C1 cada mensaje de secuencia es una operación de la clase receptora; C2 cada transición de estados corresponde a una operación de la clase; C3 multiplicidades coherentes con los criterios de aceptación; C4 paquetes sin ciclos; C5 nombres consistentes.
No reescribas los diagramas; solo reporta hallazgos y cita la línea.
```

| # | Regla | Hallazgo de la IA | Verificación del equipo | Decisión |
|---|---|---|---|---|
| H1 | C5 | En `secuencia-ingesta-alerta.puml` (línea 39) se usa `superaUmbral(150)` con el valor literal, y en `clases.puml` (línea 79) `umbralPm10 = 150`; el código usa la constante `UMBRAL_PM10` de `compartido`. | Correcto: el nombre del dominio debe coincidir en diagramas y código. | **Corregido:** ambos diagramas usan `UMBRAL_PM10`. |
| H2 | C4 | La nota de `paquetes.puml` afirma "Verificado en la CI con import-linter", pero ningún workflow ejecuta import-linter. | Correcto: `render-diagramas.yml` solo dibuja diagramas. La afirmación no tenía respaldo. | **Corregido:** la nota indica que se verificó con el diagrama de paquetes de pyreverse (`packages_airemisti.puml`). |
| H3 | C1/C5 | La actividad "Publica una rectificación en el canal" no tiene una operación que la soporte: `CanalAlertas` solo tiene `publicar(a: Alerta)` y `Alerta.mensaje()` siempre redacta el aviso de alerta. | Correcto a medias: no hace falta una operación nueva, porque `publicar()` sirve; pero `mensaje()` no consideraba el estado RETIRADA. | **Corregido en el código:** `mensaje()` redacta la rectificación si la alerta está RETIRADA (prueba `test_alerta_retirada_publica_rectificacion`). |
| H4 | C2 | `marcarSinSenal()` la provoca "una tarea programada", pero esa tarea no aparece en el diagrama de clases. | Correcto, aunque fuera del alcance de HU-03: la tarea pertenece al RF-07 (sensor sin señal). La operación sí existe en `Sensor`, que es lo que exige C2. | **Documentado:** queda la nota en `estados-sensor.mmd`; se modelará con la historia de RF-07. |
| H5 | C4 | Hay un ciclo entre `ingesta`, `alertas` y `lecturas`: `ingesta → alertas → lecturas` y `ingesta → lecturas`. | **Falso positivo.** Las dos flechas llegan a `lecturas` y ninguna sale de ella, así que no hay camino de regreso a `ingesta`. Son dos caminos que convergen, no un ciclo. El diagrama de pyreverse confirma que `lecturas` solo depende de `compartido`. | Sin cambios. |
| H6 | C1 | El mensaje 29 `mensaje()` lo envía `CanalAlertas` a `:Alerta`, pero `CanalAlertas` es una interfaz y una interfaz no puede enviar mensajes. | **Falso positivo.** La línea de vida es `CanalAlertas (TelegramAdapter)`: en ejecución quien envía el mensaje es el adaptador concreto que realiza la interfaz. Además, `mensaje()` sí es operación de `Alerta`, la clase receptora, que es lo que exige C1. | Sin cambios. |

**Resumen:** 6 hallazgos; 3 corregidos, 1 documentado y 2 falsos positivos (H5 y H6).

## 3. Validación del diagrama de actividades (E4)

Daniel revisó el diagrama como si fuera el analista municipal y observó que el ciudadano recibía el aviso **al final**, después de la revisión del analista. En la realidad el aviso llega apenas se publica en Telegram (QA-02, 60 s o menos), y si el analista retira la alerta, el ciudadano no se enteraba de la rectificación.

**Cambio aplicado por Brigitte:** la recepción del aviso por el ciudadano pasó a la rama de Telegram dentro del fork, y se agregó la actividad "Recibe la rectificación" en la rama de retiro.
