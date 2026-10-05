# ADR-003: Usar MQTT con QoS 1, sesiones persistentes y credenciales por sensor para la ingesta

- Estado: Aceptado
- Fecha: 2026-10-01
- Decisores: Daniel Josué Guillén Valcárcel y Brigitte Noelia Mengoa Valeriano

## Contexto
Los sensores tienen conectividad intermitente y recursos limitados (R-04). Deben entregar cada lectura al menos una vez (QA-01), el servidor no debe perder lecturas si la aplicación se reinicia (QA-03) y solo los sensores registrados pueden publicar (QA-04). La alerta debe verse en menos de 60 s (QA-02).

## Alternativas consideradas
1. HTTP: un POST por lectura; es conocido por el equipo, pero cada envío abre una conexión, el sensor debe programar sus propios reintentos y, si la API no está disponible, no hay nada que retenga los mensajes.
2. MQTT con QoS 0: muy liviano, pero no confirma la entrega y se pueden perder lecturas.
3. MQTT con QoS 1, sesiones persistentes y persistencia en disco del broker.

## Decisión
Usaremos la alternativa 3 con Mosquitto. Cada sensor publica en el tema `airemisti/<id_sensor>/lecturas` con QoS 1; el proceso de ingesta se conecta con una sesión persistente (`clean_session=false`) y Mosquitto se configura con `persistence true` para que los mensajes pendientes sobrevivan a un reinicio. Cada sensor tiene usuario y contraseña propios, la conexión va cifrada con TLS (puerto 8883) y una ACL solo le permite publicar en su propio tema.

## Consecuencias
- Positivas: entrega garantizada al menos una vez; los mensajes quedan retenidos si la ingesta se detiene; el protocolo consume poca batería y datos móviles; las ACL impiden que un sensor publique en nombre de otro.
- Negativas / riesgos: QoS 1 puede entregar un mensaje dos veces, lo que se resuelve con la clave única de ADR-002; el equipo debe administrar las credenciales y certificados de 40 sensores.
