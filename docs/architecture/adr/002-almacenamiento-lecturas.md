# ADR-002: Guardar las lecturas en PostgreSQL particionado por mes con clave única por sensor y hora

- Estado: Aceptado
- Fecha: 2026-09-30
- Decisores: Daniel Josué Guillén Valcárcel y Brigitte Noelia Mengoa Valeriano

## Contexto
Se generan unos 21 millones de lecturas al año. Al reconectarse tras un corte, los sensores reenvían lecturas que el servidor podría haber recibido parcialmente, por lo que pueden llegar duplicadas o desordenadas (RF-02, QA-01). El analista descarga histórico por rangos de fechas (RF-05). El equipo domina PostgreSQL (R-02) y el presupuesto no admite servicios administrados (R-03).

## Alternativas consideradas
1. InfluxDB: base de series de tiempo especializada, pero es una tecnología nueva para el equipo y obliga a mantener dos bases de datos.
2. Una sola tabla de PostgreSQL sin particionar: simple, pero las consultas de histórico y el borrado de datos antiguos se vuelven lentos con decenas de millones de filas.
3. PostgreSQL con particionado nativo por mes y clave única (sensor_id, medido_en).

## Decisión
Usaremos la alternativa 3. La tabla `lectura` se particiona por rango de `medido_en` (una partición por mes) y tiene una restricción única sobre `(sensor_id, medido_en)`. La ingesta inserta por lotes con `INSERT ... ON CONFLICT (sensor_id, medido_en) DO NOTHING`, de modo que un reenvío no genera duplicados, y cada lectura conserva la hora en que se midió, no la hora en que llegó.

## Consecuencias
- Positivas: no hay duplicados aunque un sensor reenvíe todo su backlog; las consultas por mes solo leen la partición necesaria; no se agrega ninguna tecnología nueva.
- Negativas / riesgos: hay que crear las particiones futuras; se mitiga con una tarea programada que crea la partición del mes siguiente y una partición por defecto que captura lecturas fuera de rango.
