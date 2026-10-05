# ADR-001: Adoptar un monolito modular con broker MQTT para el MVP de AireMisti IoT

- Estado: Aceptado
- Fecha: 2026-09-29
- Decisores: Daniel Josué Guillén Valcárcel y Brigitte Noelia Mengoa Valeriano

## Contexto
El MVP debe estar en producción en 1 mes (R-01) con 2 developers que dominan Python/Django y PostgreSQL, sin experiencia en Kafka ni Kubernetes (R-02), sobre un único VPS (R-03). El atributo crítico es no perder ninguna lectura de los 40 sensores, aunque la red se corte hasta 2 horas (QA-01) o la aplicación se reinicie (QA-03), y publicar alertas en menos de 60 s (QA-02). La carga es de 0,67 lecturas/s y el peor caso tras un corte es de 4800 lecturas.

## Alternativas consideradas
1. Monolito en capas con ingesta HTTP (3,95): el más simple, pero si la API no responde la lectura depende solo de los reintentos del sensor.
2. Microservicios orientados a eventos con Kafka (3,00): muy fiable y escalable, pero su operación excede la capacidad del equipo, el plazo y el presupuesto.
3. Monolito modular con broker MQTT (4,50): elegido.

## Decisión
Usaremos un monolito modular en Django con cinco módulos: Ingesta, Sensores, Lecturas e histórico, Alertas y Mapa público. Los sensores publicarán en un broker Mosquitto instalado en el mismo VPS; un proceso de ingesta del monolito se suscribirá al broker y guardará las lecturas en PostgreSQL. Los módulos se comunicarán solo mediante servicios de aplicación públicos y cada uno tendrá su propio esquema.

## Consecuencias
- Positivas: un solo servidor y un solo despliegue; el broker desacopla a los sensores de la aplicación, de modo que un reinicio de Django no pierde lecturas; se puede pasar a un broker en clúster o a servicios separados si la red de sensores crece.
- Negativas / riesgos: el VPS sigue siendo un punto único de falla, mitigado porque los sensores guardan lecturas en su microSD; el equipo debe aprender a configurar Mosquitto y respetar los límites entre módulos (import-linter en la CI).
