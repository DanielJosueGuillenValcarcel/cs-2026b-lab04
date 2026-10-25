# Métricas antes y después del refactor (E6)

Herramienta: radon 6.0.1 (`radon cc -s -a` y `radon raw -s`). Salidas completas en
`radon-antes.txt` y `radon-despues.txt`. El gráfico `img/metricas.png` se genera con
`python metricas.py`.

## Complejidad ciclomática por método

| Método | Antes | Después |
|---|:---:|:---:|
| `ServicioMonitoreo.procesar` | 26 (D) | 5 (A) |
| `ServicioMonitoreo.explicar_alerta` | 8 (B) | 1 (A) |
| `ServicioMonitoreo.__init__` | — | 6 (B) |
| `ServicioMonitoreo._actualizar_alerta` | (dentro de `procesar`) | 3 (A) |
| `Sensor.enviar_a_mantenimiento` / `dar_de_baja` | 3 (A) | 1 (A), una clase por estado |
| `FiltroAnomalias.leer` | (dentro de `procesar`) | 5 (A) |
| `ConReintentos.enviar` | (dentro de `procesar`) | 4 (A) |
| `NoInventaPM10.validar` / `SinConsejosMedicos.validar` | (dentro de `explicar_alerta`) | 3 (A) / 3 (A) |
| **Complejidad máxima** | **26 (D)** | **6 (B)** |
| **Promedio** | **6,2 (B), 10 bloques** | **1,74 (A), 128 bloques** |

## Tamaño

| | Antes | Después |
|---|:---:|:---:|
| Archivos | 1 | 6 (`servicio`, `sensores`, `indices`, `estados`, `eventos`, `ia`) |
| SLOC | 127 | 356 (71 + 44 + 22 + 78 + 62 + 79) |
| Clases | 4 | 39 |
| Pruebas del flujo | 20 casos sobre antes | 20 casos × 2 versiones + 29 de patrones |

![Métricas](img/metricas.png)

## Trade-off

Ganamos un método principal que se lee de arriba abajo (complejidad 26 → 5) y la posibilidad de
agregar una marca de sensor, una norma, un canal de aviso o un proveedor de IA sin modificar
`ServicioMonitoreo`: las pruebas `test_marca_nueva_se_registra_sin_tocar_el_servicio`,
`test_norma_nueva_se_agrega_sin_tocar_el_servicio` y `test_suscriptor_nuevo_recibe_las_alertas`
lo demuestran. El refactor además corrigió el error del estado `SIN_SENAL`. El costo es real: el
código casi se triplica (127 → 356 SLOC), pasa de 1 a 6 archivos y para seguir una lectura hay
que saltar entre fábrica, adaptador, decorador, estado y publicador. Si AireMisti solo fuera a usar
sensores AireSense, una sola norma y nunca IA, la versión antes, con un par de métodos extraídos,
habría sido suficiente. Los patrones se justifican porque el municipio ya compró dos marcas y el
caso pide comparar ECA con OMS y explicar alertas con IA.

## Patrones que decidimos NO aplicar

| Patrón | Por qué no |
|---|---|
| Singleton (fábricas) | Estado global que se filtra entre pruebas; se inyecta la fábrica en el servicio. |
| Proxy de caché de lecturas | No hay consultas repetidas en este flujo; Redis ya es la caché (ADR-002). |
| Abstract Factory | Solo hay una familia de productos por fábrica; una Factory con registro basta. |
| LLM como juez de otro LLM | Duplica costo y latencia para un MVP de 1 mes; las reglas deterministas son verificables con pruebas. |
| Command para las alertas | No hace falta deshacer ni encolar avisos; Observer cubre el caso. |

## Deuda que queda

`src/airemisti/ingesta/servicio.py::ServicioIngesta.procesar_lote` (Lab 05) tiene complejidad 13 (C).
No está en el flujo refactorizado de este laboratorio; queda como candidato para el siguiente.
