# Drivers arquitectónicos — AireMisti IoT

## 1. Requisitos funcionales clave
| ID    | Requisito                                                                                     | Actor              | Prioridad |
|-------|-----------------------------------------------------------------------------------------------|--------------------|-----------|
| RF-01 | El sensor envía una lectura de PM10 y PM2.5 cada minuto                                       | Sensor             | Alta      |
| RF-02 | El sensor guarda localmente las lecturas durante un corte de red y las reenvía al reconectarse | Sensor             | Alta      |
| RF-03 | El ciudadano consulta un mapa en tiempo real con el nivel de cada sensor                      | Ciudadano          | Alta      |
| RF-04 | El sistema emite una alerta pública cuando PM10 supera 150 µg/m³                              | Sistema            | Alta      |
| RF-05 | El analista descarga el histórico por sensor y rango de fechas en CSV                         | Analista municipal | Media     |
| RF-06 | El analista registra, ubica en el mapa y da de baja sensores                                  | Analista municipal | Media     |
| RF-07 | El sistema avisa al analista cuando un sensor no reporta durante más de 10 minutos            | Sistema            | Media     |

## 2. Atributos de calidad (ordenados por prioridad)
1. **Fiabilidad de la ingesta** — no se puede perder ninguna lectura, aunque la red se corte hasta 2 horas; un vacío en la serie invalida los promedios que usa la municipalidad.
2. **Integridad de los datos** — al reenviar lecturas acumuladas no deben duplicarse ni desordenarse.
3. **Rendimiento de las alertas** — la población debe enterarse de un pico de contaminación en menos de un minuto.
4. **Disponibilidad** — si la aplicación web se reinicia, las lecturas que llegan en ese momento no deben perderse.
5. **Seguridad (autenticidad)** — solo los sensores registrados pueden publicar lecturas; datos falsos generarían alertas falsas.

## 3. Restricciones
| ID   | Tipo        | Restricción                                                                                          |
|------|-------------|------------------------------------------------------------------------------------------------------|
| R-01 | Plazo       | MVP en producción en 1 mes                                                                           |
| R-02 | Equipo      | 2 developers con experiencia en Python (Django, FastAPI) y PostgreSQL; sin experiencia en Kafka ni Kubernetes |
| R-03 | Presupuesto | Un único VPS de bajo costo (≈ 4 vCPU / 8 GB); sin servicios IoT de pago en la nube                   |
| R-04 | Tecnología  | 40 sensores con conectividad intermitente (WiFi/4G) y memoria microSD para almacenamiento local      |
| R-05 | Normativa   | Los datos se publican como información pública y se contrastan con los Estándares de Calidad Ambiental para Aire (D.S. N.° 003-2017-MINAM) |

## 4. Escenarios de atributos de calidad
| ID    | Atributo       | Fuente             | Estímulo                                                   | Entorno                         | Artefacto                    | Respuesta                                                           | Medida |
|-------|----------------|--------------------|------------------------------------------------------------|---------------------------------|------------------------------|---------------------------------------------------------------------|--------|
| QA-01 | Fiabilidad     | Sensor             | Pierde la red 2 h y al volver reenvía 120 lecturas acumuladas | Recuperación tras corte de red  | Broker MQTT + módulo Ingesta | Acepta todas las lecturas con su hora original, sin duplicados       | 0 lecturas perdidas; 0 duplicadas; backlog procesado en ≤ 5 min |
| QA-02 | Rendimiento    | Sensor             | Envía una lectura con PM10 = 180 µg/m³                     | Operación normal                | Módulo Alertas               | Marca el sensor en rojo en el mapa y publica la alerta               | Alerta visible en ≤ 60 s (p95) |
| QA-03 | Disponibilidad | Servidor           | La aplicación Django se reinicia o cae                     | Operación normal                | Broker MQTT persistente      | El broker retiene las lecturas y la ingesta las procesa al volver    | 0 lecturas perdidas en caídas de hasta 10 min; mapa disponible de nuevo en ≤ 5 min |
| QA-04 | Seguridad      | Dispositivo externo | Intenta publicar lecturas sin credenciales válidas          | Operación normal                | Broker MQTT                  | Rechaza la conexión y registra el intento                            | 100 % de conexiones no autorizadas rechazadas |

### Verificación de QA-01
Carga normal: 40 sensores × 1 lectura/min = 0,67 lecturas/s. Peor caso: los 40 sensores reconectan a la vez con 120 lecturas cada uno = 4800 lecturas. Insertando por lotes en PostgreSQL a un ritmo conservador de 100 lecturas/s, el backlog se procesa en 48 s, muy por debajo de los 5 min. Volumen anual: 40 × 1440 × 365 ≈ 21 millones de filas. Se verifica con un simulador de 40 sensores que corta la red 2 h y compara las lecturas enviadas con las almacenadas.
