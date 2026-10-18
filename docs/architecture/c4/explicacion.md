# AireMisti IoT explicado para la municipalidad

Público: gerente de Gestión Ambiental de la Municipalidad de Arequipa (no técnico). Basado en la [vista de contexto](img/structurizr-Contexto.png).

AireMisti es un servicio que mide la contaminación del aire en Arequipa con 40 sensores repartidos por la ciudad. Cada sensor envía una medición por minuto y, si se queda sin internet, la guarda y la reenvía al reconectarse, así no se pierde ningún dato. Los vecinos ven en un mapa cómo está el aire en su zona, y el analista de la municipalidad registra sensores y descarga el historial. Cuando la contaminación supera el límite permitido, AireMisti publica una alerta en un canal público de Telegram en menos de un minuto. El mapa de fondo proviene de OpenStreetMap, un servicio gratuito.

*(102 palabras)*

## Verificación contra el modelo

| Afirmación | ¿Es cierta? | Evidencia |
|---|---|---|
| 40 sensores, una medición por minuto | Sí | Sistema externo "Red de sensores", RF-01 |
| Guardan y reenvían durante los cortes | Sí | Descripción del sensor (microSD), RF-02, QA-01 |
| Mapa para vecinos; el analista registra sensores y descarga el historial | Sí | Relaciones de Ciudadano y Analista municipal |
| Alerta en Telegram en menos de un minuto | Sí | "Publica alertas de contaminación", QA-02 (≤ 60 s) |
| Mapa de fondo de OpenStreetMap | Sí | "Obtiene las teselas del mapa" |

**Ajustes de la revisión:** se evitó decir que "todos los vecinos reciben la alerta en su celular", porque solo la reciben quienes siguen el canal de Telegram, y que "los datos se guardan en la nube de forma segura", porque la vista de contexto no muestra dónde se guardan. Tampoco se mencionan tecnologías (MQTT, Django), que no aportan a este público.
