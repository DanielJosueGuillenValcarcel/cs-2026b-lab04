# ADR-008: Credenciales por sensor con una ACL de patrón y altas por recarga del broker

- Estado: Aceptado
- Fecha: 2026-10-30
- Decisores: Daniel Josué Guillén Valcárcel y Brigitte Noelia Mengoa Valeriano

## Contexto
Con 400 sensores, una credencial filtrada es más probable. Un sensor no debe poder publicar en el tema de otro (QA-06), porque una lectura falsa genera una alerta falsa. El analista debe poder dar de alta 50 sensores en ≤ 1 h sin reiniciar el broker ni desplegar código (QA-08). ADR-003 ya define usuario y contraseña por sensor y TLS.

## Alternativas consideradas
1. Una contraseña compartida: alta inmediata, pero una sola filtración compromete a los 400 sensores.
2. Una línea de ACL por sensor: aísla, pero son 400 líneas que mantener a mano.
3. Usuario y contraseña por sensor y una ACL con patrón (`pattern write airemisti/%u/lecturas`): una regla para todos.
4. Certificado de cliente por sensor (mTLS): el mejor aislamiento, pero exige una CA y renovar 400 certificados.

## Decisión
Se adopta la alternativa 3. El código del sensor es su usuario MQTT y solo puede escribir en su propio tema. Solo el usuario `ingesta` lee todos los temas y publica los acuses. Las altas se hacen con `mosquitto_passwd` y `systemctl reload mosquitto` (SIGHUP).

## Consecuencias
- Positivas: medido con Mosquitto real, 0 publicaciones cruzadas aceptadas y anónimos y claves incorrectas rechazados; 50 altas en 0,7 s sin cortar la conexión de la ingesta. FF-08, FF-11 y FF-12 lo verifican.
- Negativas / riesgos: una clave robada aún permite enviar datos falsos del propio sensor (riesgo R4); se mitiga con la retirada de alertas por el analista. Se revisará mTLS si la red supera los 1000 sensores.
