# E6. Humano en el circuito y delegación progresiva — AireMisti IoT

## Aprobación humana de ediciones
`politica.aprobar_por_consola` muestra la edición propuesta (archivo, antes y después) y solo acepta `s` o `n`; cualquier otra respuesta se vuelve a pedir. Se activa con `--aprobar`, que asigna la función a `aprobar_edicion` en la política del ejecutor:

```
python orquestador.py --issue 01 --modo unico --aprobar
```

Una edición rechazada vuelve al agente como observación `BLOQUEADO POR LA POLÍTICA: El revisor humano rechazó la edición`. Las ediciones en `tests/` se bloquean antes de preguntar: el humano no puede aprobar por error que el agente debilite una prueba. `pruebas_agente/test_humano.py` lo verifica.

## Hoja de ruta de autonomía

| Etapa (rol humano) | Qué hace el agente | Permisos del agente | Evidencia de las trazas para pasar a la siguiente etapa |
|---|---|---|---|
| 1. Ejecutor (el humano hace el trabajo) | Solo lee y explica: ubica la causa del issue y propone el cambio en texto | `listar_archivos`, `leer_archivo`, `buscar`, `mapa_repo`; sin editar ni ejecutar | En 10 issues seguidos la causa propuesta coincide con la que corrige el humano, con 0 rechazos del contrato |
| 2. Revisor (estado actual) | Edita en el sandbox y ejecuta pruebas; el humano aprueba cada edición en consola y fusiona el PR | + `editar_archivo` con aprobación, `ejecutar_pruebas`, `python -m pytest`; `tests/` protegida; máx. 12 pasos | En 20 issues: ≥ 90 % de ediciones aprobadas sin cambios, 0 intentos de editar `tests/`, 0 acciones bloqueadas por comandos fuera de la lista y ningún PR revertido |
| 3. Colaborador | Edita sin aprobación por edición dentro de `src/airemisti/reportes` y abre el PR en una rama; el humano revisa el PR completo | Edición libre solo en `reportes/`; aprobación por edición solo fuera de ese módulo; revisor de solo lectura obligatorio | Un mes sin regresiones en CI atribuibles al agente, revisor y humano de acuerdo en ≥ 95 % de los veredictos y costo por issue estable en las trazas |
| 4. Gobernador | Resuelve issues de reportes de punta a punta y fusiona si CI y el revisor aprueban; el humano define políticas, audita trazas y puede detenerlo | Fusión automática solo en `reportes/`; nunca en ingesta, alertas ni configuración de Mosquitto (ADR-006 a ADR-008) | Auditoría mensual de trazas sin hallazgos; ante cualquier PR revertido, el agente vuelve a la etapa 3 |

## Límites que no cambian con la etapa
- El agente nunca toca la ingesta MQTT, las alertas públicas ni las credenciales de los sensores: un error ahí pierde lecturas (QA-01) o publica una alerta falsa en Telegram.
- Sin red, sin git y sin credenciales reales en ninguna etapa; trabaja en una copia (`agentes/trabajo/`).
- Ningún agente fusiona su propio cambio mientras esté en las etapas 1 a 3.
