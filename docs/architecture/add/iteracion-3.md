# Iteración 3 de ADD — Aislamiento entre sensores y altas sin reiniciar (QA-06 y QA-08)

## 1. Entradas revisadas
[ADR-003](../adr/003-protocolo-ingesta.md) (usuario y contraseña por sensor, TLS y ACL), los escenarios QA-04, QA-06 y QA-08 del
[árbol de utilidad](../utilidad/escenarios.md) y el riesgo R4 del [ATAM-lite](../atam-lite.md).

## 2. Objetivo
- **QA-06 (H,M):** un sensor con credenciales robadas no puede publicar en el tema de otro sensor (0 publicaciones cruzadas aceptadas).
- **QA-08 (H,M):** dar de alta 50 sensores en ≤ 1 h, sin reiniciar el broker ni desplegar código.

## 3. Elemento que se refina
La autenticación y la autorización del **Broker MQTT**, y el procedimiento de alta de sensores del módulo **Sensores**.

## 4. Conceptos de diseño evaluados
La seguridad no se puede simular igual que la latencia, así que se compararon alternativas y después se verificó la elegida con el broker real.

| Alternativa | Aislamiento (QA-06) | Alta de sensores (QA-08) | Decisión |
|---|---|---|---|
| Una contraseña compartida por todos los sensores | Nulo: cualquiera publica como cualquiera | Inmediata | **Rechazada:** una sola clave filtrada compromete a los 400 |
| Usuario y contraseña por sensor + una línea de ACL por sensor | Alto | 400 líneas que mantener; un error de copia abre un tema | **Rechazada:** propensa a errores |
| Usuario y contraseña por sensor + ACL con patrón `pattern write airemisti/%u/lecturas` | Alto: cada usuario solo escribe en su tema | Una línea en el archivo de contraseñas y recarga con `SIGHUP` | **Aceptada** |
| Certificado de cliente por sensor (mTLS) | Muy alto: la identidad no se puede copiar sin la clave privada | Lento: generar, instalar y renovar 400 certificados; el equipo no tiene una CA | **Rechazada para el MVP;** se revisará con más de 1000 sensores |

## 5. Elementos instanciados
- [infra/mosquitto/acl](../../../infra/mosquitto/acl): los sensores escriben solo en `airemisti/%u/lecturas` y leen `airemisti/%u/ack`; solo el usuario `ingesta` lee todos los temas.
- [mosquitto.conf](../../../infra/mosquitto/mosquitto.conf): `allow_anonymous false`, `password_file` y `acl_file`.
- Alta de sensores: `mosquitto_passwd -b /etc/mosquitto/passwd <código> <clave>` por cada sensor y luego `systemctl reload mosquitto` (envía `SIGHUP`, sin cortar conexiones).

## 6. Evidencia (experimento real con Mosquitto 2.0.18)
| Prueba | Resultado |
|---|---|
| AQP-0001 publica en su propio tema | Aceptada (1) |
| AQP-0001 publica en el tema de AQP-0002 y en `airemisti/todos/lecturas` | **0 aceptadas** |
| Cliente anónimo | Rechazado |
| Usuario correcto con clave incorrecta | Rechazado |
| Alta de 50 sensores con 400 ya registrados | 0,7 s; los 50 publicaron; la ingesta **no se desconectó** |

**Trade-off aceptado:** una clave robada todavía permite enviar datos falsos **del propio sensor** y generar una alerta falsa en su distrito. Se mitiga porque el analista puede retirar la alerta (`Alerta.retirar` publica una rectificación, Lab 05) y se acepta porque los certificados no caben en el plazo.

## 7. ¿Se cumple el escenario?
- **QA-06: sí.** 0 publicaciones cruzadas.
- **QA-04:** se mantiene (100 % de conexiones sin credenciales rechazadas).
- **QA-08: sí.** 50 altas en menos de 1 s de trabajo del broker, sin reinicio.
- Fitness functions: FF-08 (ninguna regla de escritura de la ACL sin `%u`), FF-11 y FF-12 (Mosquitto real). Decisión registrada en el [ADR-008](../adr/008-credenciales-por-sensor-y-acl-con-patron.md).
