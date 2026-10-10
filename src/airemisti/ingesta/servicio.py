from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable

from airemisti.compartido.parametros import UMBRAL_PM10
from airemisti.lecturas.dominio import Lectura, RepositorioLecturas
from airemisti.sensores.dominio import EstadoSensor, RepositorioSensores

log = logging.getLogger(__name__)


class ServicioIngesta:
    def __init__(self, sensores: RepositorioSensores, lecturas: RepositorioLecturas,
                 encolar_alerta: Callable[[Lectura, str], None]) -> None:
        self.sensores = sensores
        self.lecturas = lecturas
        self.encolar_alerta = encolar_alerta

    def procesar_lote(self, codigo_sensor: str, datos: list[dict[str, Any]]) -> int:
        sensor = self.sensores.buscar_por_codigo(codigo_sensor)
        if sensor is None or not sensor.esta_habilitado():
            log.warning("Lectura rechazada de %s", codigo_sensor)
            return 0
        if len(datos) > 1 and sensor.estado == EstadoSensor.SIN_SENAL:
            sensor.iniciar_sincronizacion()
        lote = []
        for d in datos:
            lectura = Lectura(
                sensor_id=sensor.id,
                pm10=Decimal(str(d["pm10"])),
                pm25=Decimal(str(d["pm25"])),
                medido_en=datetime.fromisoformat(d["medido_en"]),
            )
            if lectura.es_valida():
                lote.append(lectura)
        if not lote:
            return 0
        insertadas = self.lecturas.guardar_lote(lote)
        sensor.registrar_lectura(max(l.medido_en for l in lote))
        if sensor.estado == EstadoSensor.SINCRONIZANDO:
            sensor.completar_sincronizacion()
        self.sensores.guardar(sensor)
        sobre_umbral = [l for l in lote if l.supera_umbral(UMBRAL_PM10)]
        if sobre_umbral:
            pico = max(sobre_umbral, key=lambda l: l.pm10)
            self.encolar_alerta(pico, sensor.ubicacion.distrito)
        return insertadas
