# ADR-010: Arquitectura del sistema agéntico para corregir issues

- Estado: Aceptado
- Fecha: 2026-11-20
- Decisores: Daniel Josué Guillén Valcárcel y Brigitte Noelia Mengoa Valeriano

## Contexto
El analista municipal reporta errores en el resumen diario (RF-05) que exigen leer el código para hallar la causa: los pasos no se conocen de antemano. Un error en datos agregados puede ocultar lecturas (QA-01) o alertas (RF-04). El equipo es de dos personas, no tiene clave de API y el agente no debe tocar producción, credenciales de sensores ni la ingesta MQTT (ADR-003, ADR-008). Cada issue tiene una prueba que falla (`tests/test_issue_0N.py`), que define objetivamente cuándo está resuelto. Las trazas de E2, E4, E5 y el Reto A están en `agentes/observacion.md`.

## Alternativas consideradas
1. Flujo de trabajo fijo (leer, editar, probar): barato y predecible, pero no sabe dónde buscar la causa cuando cambia el issue.
2. Agente único ReAct con política, contrato y humano que aprueba: 8 pasos y ~14 000 caracteres por issue en las trazas.
3. Planificador + actor-crítico (ejecutor y revisor de solo lectura, máx. 2 rondas): mismo cambio en ISSUE-02 con 16 pasos y 2,9 veces el contexto.
4. Coordinación democrática (tres revisores que votan): mismo veredicto unánime con 24 pasos y 4,2 veces el contexto del agente único.
5. Agente con acceso a git y fusión automática: descartado por exceso de agencia (OWASP LLM06) mientras la confianza sea baja.

## Decisión
Usaremos la alternativa 2 para errores acotados del módulo de reportes y la 3 solo cuando el cambio toque ingesta o alertas.
- **Arquetipo:** ReAct; en modo actor-crítico, un planificador sin herramientas que produce un plan de 3 a 5 pasos.
- **Herramientas:** `listar_archivos`, `leer_archivo`, `buscar`, `mapa_repo`, `editar_archivo`, `ejecutar_pruebas`, `ejecutar_comando` (solo `python -m pytest`) y las notas `anotar`/`leer_notas`. El revisor solo lee y ejecuta pruebas.
- **Memoria:** historial de la tarea y notas en `notas.md` dentro del sandbox; sin memoria entre ejecuciones.
- **Límites:** contrato JSON validado antes de la política; política por rol; `tests/` protegida; 12 pasos para el ejecutor, 8 para el revisor, 2 para el planificador y 2 rondas; sandbox `agentes/trabajo/` sin red ni git.
- **Rol humano:** revisor (etapa 2 de `agentes/delegacion.md`): aprueba cada edición en consola (`--aprobar`) y fusiona el Pull Request. El cambio aprobado lo aplica un integrante en `src/`.

## Consecuencias
- Positivas: los tres issues quedaron resueltos sin tocar las pruebas, con 0 acciones bloqueadas y 0 rechazos del contrato en las corridas. Cada corrida queda grabada (`trayectorias/`) y se reproduce sin modelo, también en CI (`pruebas.yml`). Las pruebas del contrato encontraron dos defectos del framework (`final` con campos extra y `accion` como lista).
- Negativas / riesgos: el agente depende de que el issue tenga una prueba objetiva; sin ella el actor-crítico vuelve a ser necesario. `ejecutar_pruebas` oculta los nombres de las pruebas que fallan y cuesta un paso extra por corrida. El modelo grabado no detecta cambios de comportamiento del modelo real: las trayectorias deben regrabarse si cambia el modelo o el prompt. El filtro de seguridad del modelo puede rechazar una decisión válida y obligar a reintentar.
