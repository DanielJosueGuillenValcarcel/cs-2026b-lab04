# Lienzo de diseño del sistema agéntico — AireMisti IoT

**Tarea del sistema:** corregir errores reportados en el módulo de reportes del analista municipal (`src/airemisti/reportes/`, RF-05), cada uno descrito en `issues/ISSUE-0N.md` con una prueba que lo reproduce.

| Decisión de diseño | Elección para AireMisti IoT | Justificación |
|---|---|---|
| ¿Agente o flujo de trabajo? | Agente para corregir issues; flujo fijo para todo lo que toca lecturas en producción | La causa de cada issue hay que encontrarla leyendo el código: los pasos no se conocen de antemano. La ingesta MQTT, las alertas y el despliegue siguen siendo flujos deterministas (ADR-006/007): un agente ahí agregaría latencia y riesgo sin beneficio |
| Arquetipo | Planificador-ejecutor + ReAct | El plan corto (3 a 5 pasos) se revisa de un vistazo; el ejecutor explora con ReAct porque cada observación (traceback, archivo) cambia el siguiente paso |
| Herramientas | `listar_archivos`, `leer_archivo`, `buscar`, `editar_archivo`, `ejecutar_pruebas`, `ver_cambios`, `ejecutar_comando` (solo `python -m pytest`); en E4 `mapa_repo`, `anotar`, `leer_notas` | Lo mínimo para leer, cambiar y verificar. Sin red, sin git, sin acceso a Mosquitto, PostgreSQL ni al bot de Telegram (mínimo privilegio, OWASP LLM06) |
| Memoria | Historial de la tarea (corto plazo) + notas de trabajo en `notas.md` (E4) | Los issues son cortos y no requieren recordar ejecuciones previas; las notas guardan hipótesis y archivos revisados para no releerlos y reducir el contexto |
| Coordinación | Agente único para issues de una línea; por gestor (planificador) + actor-crítico (ejecutor y revisor de solo lectura) para cambios que afectan datos agregados | Separar quién cambia el código de quién lo revisa; el revisor no puede editar ni ejecutar comandos. Se aplica parsimonia: más agentes solo cuando el error puede ocultar lecturas (ISSUE-02) |
| Rol humano | Revisor: aprueba cada edición en consola (`aprobar_edicion`) y fusiona el Pull Request | Primer uso del sistema y datos que alimentan alertas públicas: la confianza todavía es baja |
| Control | Contrato JSON, política por rol, `tests/` protegida, máx. 12 pasos (ejecutor), 8 (revisor), máx. 2 rondas, sandbox en `agentes/trabajo/` | Evitar acciones indebidas, que el agente "arregle" las pruebas, bucles y costos sin límite; nunca trabaja sobre `src/` ni con credenciales reales |

## Tareas que se resuelven mejor con un flujo fijo
- Regenerar diagramas, calcular métricas con radon y ejecutar import-linter: ya los hace GitHub Actions sin modelo.
- Aplicar el cambio aprobado en `src/` y fusionar: lo hace un integrante del grupo.
