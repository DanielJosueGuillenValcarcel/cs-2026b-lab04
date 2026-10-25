# Verificación de clases.puml con pyreverse (E7)

```bash
cd src
pyreverse -o puml -p monitoreo monitoreo --ignore antes
java -jar plantuml.jar -tpng -o img classes_monitoreo.puml packages_monitoreo.puml
```

Resultado: [classes_monitoreo.puml](classes_monitoreo.puml) e [img/classes_monitoreo.png](img/classes_monitoreo.png).
Se comparó con [../clases.puml](../clases.puml) (actualizado en este laboratorio) y con los
diagramas por patrón de esta carpeta.

| # | Diferencia observada | Causa | Acción |
|:---:|---|---|---|
| 1 | `AireSenseAdapter`, `PurairAdapter` y `FiltroAnomalias` no aparecen unidos a `LectorSensor`; lo mismo pasa con `OpenAIAdapter`/`GeminiAdapter` y `ProveedorLLM`. | Los puertos son `typing.Protocol` (tipado estructural): las clases cumplen la interfaz sin heredar de ella, y pyreverse solo dibuja herencia explícita. | **Documentar.** El diseño mantiene la realización `<|..`, que es la intención. |
| 2 | `Sensor` no muestra la agregación con `EstadoSensor`. | El estado se guarda en `_estado` y se crea con `estado or Activo()`; pyreverse no infiere el tipo. | **Documentar.** La relación está en `state.puml` y la prueban `test_transiciones_*`. |
| 3 | Los observadores heredan de `SuscriptorBase`, que no está en el diseño. | Clase de conveniencia con métodos vacíos para que cada suscriptor implemente solo el evento que le interesa. | **Corregir el diagrama:** se nombra en `observer-decorator.puml` como implementación de `Suscriptor`. |
| 4 | En el código las fábricas `FabricaNormas` y `FabricaProveedores` existen, aunque `clases.puml` solo muestra `FabricaLectores`. | `clases.puml` es la vista de los módulos del Lab 05; las otras fábricas son detalle de `strategy.puml` e `ia.puml`. | **Documentar.** |
| 5 | `ServicioMonitoreo` aparece con flechas a `FabricaLectores`, `FabricaProveedores` y `PublicadorEventos` como atributos. | Se inyectan por constructor. Coincide con las dependencias `..>` del diseño. | Sin cambio. |
