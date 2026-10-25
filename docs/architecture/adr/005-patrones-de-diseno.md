# ADR-005: Aplicar patrones de diseño en el flujo de procesamiento de lecturas y alertas

- Estado: Aceptado
- Fecha: 2026-10-25
- Decisores: Daniel Josué Guillén Valcárcel y Brigitte Noelia Mengoa Valeriano

## Contexto
`ServicioMonitoreo.procesar()` (la secuencia de ingesta y alerta del Lab 05) tenía complejidad ciclomática 26 (rango D). Cada marca de sensor nueva, cada norma de calidad, cada canal de aviso o proveedor de IA obligaba a modificar ese método. El municipio ya compró sensores de dos marcas (AireSense y Purair), el caso pide clasificar con el ECA peruano y con la guía OMS 2021, y se agrega una función de IA que explica las alertas a la ciudadanía. La salida del LLM no es confiable: puede inventar un valor de PM10 o dar consejos médicos. Además, las pruebas de caracterización revelaron un error: un sensor `SIN_SENAL` volvía a `ACTIVO` aunque su payload no se pudiera leer.

## Alternativas consideradas
1. Mantener la versión antes y solo extraer métodos: barato, pero cada variante nueva sigue tocando el servicio.
2. Aplicar solo los patrones que eliminan un olor concreto (ver `docs/design/patrones/olores.md`).
3. Aplicar todos los patrones que propuso la IA, incluidos Proxy, Singleton y Abstract Factory.

## Decisión
Se adopta la alternativa 2:
- **Adapter + Factory** para leer el payload de cada marca (`sensores.py`) y **Decorator** `FiltroAnomalias` para descartar valores imposibles.
- **Strategy** `NormaCalidad` (ECA u OMS) con su fábrica (`indices.py`).
- **State** para el ciclo de vida del Sensor, igual a `estados-sensor.mmd` del Lab 05 (`estados.py`).
- **Observer** para el mapa, Telegram y el analista; **Adapter** de Telegram y **Decorator** `ConReintentos` (`eventos.py`).
- **Adapter** por proveedor de LLM, **Decorator** `ConCache` y **Chain of Responsibility** de guardrails (`ia.py`).

Las fábricas se inyectan en el servicio. Se rechazan Singleton (estado global), Proxy de caché (Redis ya cumple ese papel, ADR-002), Abstract Factory (una sola familia de productos) y el uso de un LLM como juez (costo y latencia).

## Consecuencias
- Positivas: complejidad máxima 6 y promedio 1,74 (antes 26 y 6,2); una marca, norma, suscriptor o guardrail nuevo se agrega sin modificar `ServicioMonitoreo` (lo demuestran las pruebas de `test_patrones.py`); la IA se prueba sin clave de API ni red; se corrigió el error del estado `SIN_SENAL`.
- Negativas / riesgos: el código pasó de 127 a 356 SLOC y de 1 a 6 archivos; seguir una lectura exige saltar entre varias clases y el equipo debe conocer los patrones. El orden de los avisos depende del orden de suscripción en el Observer, por lo que se fija en un solo lugar (`_publicador_por_defecto`).
