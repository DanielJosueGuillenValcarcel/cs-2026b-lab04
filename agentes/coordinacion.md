# E5. Coordinación: agente único frente a actor-crítico (ISSUE-02)

Las dos variantes usan las mismas herramientas (`--memoria`), el mismo issue y el mismo sandbox. Datos tomados de `trazas/issue02-unico/` y `trazas/issue02-multi/` con `python agente/traza.py`.

| Métrica | Agente único | Planificador + ejecutor + revisor |
|---|---|---|
| Rondas actor-crítico | — | 1 de 2 (el revisor aprobó en la primera) |
| Pasos (decisiones del modelo) | 8 | 16 (planificador 1, ejecutor 8, revisor 7) |
| Acciones ejecutadas | 7 | 13 (ejecutor 7, revisor 6) |
| Rechazos del contrato | 0 | 0 |
| Acciones bloqueadas por la política | 0 | 0 |
| Contexto final del agente más cargado | 13 696 caracteres (~3424 tokens) | 20 228 caracteres (~5057 tokens), el ejecutor |
| Contexto total de la corrida | 13 696 caracteres | 39 739 caracteres (2,9 veces) |
| Cambio propuesto | clave `(m.sensor, m.medido_en)` en `sin_duplicados` | el mismo cambio, línea por línea |
| Prueba del issue | 3 de 3 | 3 de 3 |

## ¿El revisor encontró algo que el agente único pasó por alto?
No. El cambio es idéntico. El revisor aportó verificación, no hallazgos: comprobó el diff real con `ver_cambios` en lugar de creer el resumen, leyó las pruebas de los tres issues para atribuir los 4 fallos restantes a ISSUE-01 e ISSUE-03 y confirmó que no eran regresiones. El agente único llegó a la misma atribución por su cuenta. El planificador, en cambio, agregó trabajo innecesario: pidió revisar una restricción `UNIQUE` y una migración que no existen, y el ejecutor tuvo que ampliar su búsqueda (`UNIQUE|ON CONFLICT`) para descartarlo.

## Conclusión (parsimonia)
Para un issue de una función y una prueba objetiva, el actor-crítico costó el doble de pasos y casi el triple de contexto sin cambiar el resultado. La prueba del issue ya hace de crítico objetivo, y el humano revisa el diff de todas formas antes de fusionar. En AireMisti usaremos un agente único para errores acotados del módulo de reportes. El revisor de solo lectura se justifica cuando el cambio toca la ingesta o las alertas (QA-01, QA-02), donde un error silencioso pierde lecturas o emite una alerta pública falsa y no siempre hay una prueba que lo detecte. El costo extra es aceptable solo cuando el revisor puede encontrar algo que las pruebas no cubren.
