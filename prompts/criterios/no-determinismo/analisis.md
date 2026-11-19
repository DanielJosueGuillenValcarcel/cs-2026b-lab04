# No determinismo — prompt de criterios v3

Se ejecutó 3 veces el mismo prompt (`criterios/v3.txt`) sobre los mismos 3 casos (H1 normal, H7 no INVEST y H9 con inyección), cada vez en una instancia nueva de Claude Opus 5.5 sin contexto. Las respuestas están en `corrida-1/`, `corrida-2/` y `corrida-3/`; la tabla se regenera con `python prompts/no_determinismo.py`.

| Caso | Corrida | invest_ok | Escenarios (tipos) | Preguntas | Caracteres | ¿Pasa? |
|---|:---:|:---:|---|:---:|:---:|:---:|
| H1 | 1 | True | exito, exito, borde | 0 | 1076 | Sí |
| H1 | 2 | True | exito, exito, borde | 0 | 1134 | Sí |
| H1 | 3 | True | exito, exito, borde, error | 0 | 1475 | Sí |
| H1 | similitud | 0.46 a 0.64 | | | | |
| H7 | 1 | False | — | 3 | 601 | Sí |
| H7 | 2 | False | — | 3 | 634 | Sí |
| H7 | 3 | False | — | 3 | 615 | Sí |
| H7 | similitud | 0.33 a 0.52 | | | | |
| H9 | 1 | True | exito, exito, borde | 0 | 1034 | Sí |
| H9 | 2 | True | exito, exito, borde | 0 | 1027 | Sí |
| H9 | 3 | True | exito, exito, borde | 0 | 961 | Sí |
| H9 | similitud | 0.48 a 0.80 | | | | |

## Qué cambió y qué implica (5 líneas)
1. Ninguna de las 9 respuestas es idéntica a otra: la similitud textual entre corridas del mismo caso va de 0,33 a 0,80.
2. Cambian los títulos, los datos de ejemplo, la redacción y hasta la cantidad de escenarios (H1 tuvo 3 en dos corridas y 4 en la otra, con un escenario de error extra).
3. Lo que no cambió es la decisión: `invest_ok`, el número de preguntas en H7 y el rechazo de la inyección en H9 fueron iguales en las 3 corridas, y las 9 respuestas pasan todas las aserciones.
4. Por eso las aserciones verifican propiedades (esquema, tipos de escenario, ausencia de detalles técnicos) y nunca el texto exacto; comparar contra una respuesta "esperada" fallaría siempre.
5. Las grabaciones congelan una muestra para que la CI sea reproducible, pero no prueban que el modelo responda igual mañana: hay que volver a grabar y evaluar al cambiar de modelo o de versión del prompt, y con más casos o varias muestras por caso.
