from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

from airemisti.compartido.parametros import UMBRAL_PM10, VENTANA_ALERTA_PUBLICA
from airemisti.lecturas.dominio import Lectura, RepositorioLecturas
from airemisti.sensores.dominio import EstadoSensor, RepositorioSensores

log = logging.getLogger(__name__)

EncolarPico = Callable[[Lectura, str], None]


class ServicioIngesta:
    """Guarda lotes de lecturas y separa los picos en vivo de los del backlog (ADR-006).

    `encolar_alerta` va a la cola "alertas" (alerta pública); `encolar_historico` va a la cola
    "historico" (aviso al analista), para que el backlog de un corte no retrase las alertas en vivo.
    """

    def __init__(self, sensores: RepositorioSensores, lecturas: RepositorioLecturas,
                 encolar_alerta: EncolarPico, encolar_historico: EncolarPico | None = None,
                 reloj: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.sensores = sensores
        self.lecturas = lecturas
        self.encolar_alerta = encolar_alerta
        self.encolar_historico = encolar_historico
        self.reloj = reloj

    def procesar_lote(self, codigo_sensor: str, datos: list[dict[str, Any]]) -> int:
        return self.procesar(codigo_sensor, datos)[0]

    def procesar(self, codigo_sensor: str, datos: list[dict[str, Any]]) -> tuple[int, datetime | None]:
        """Devuelve (lecturas nuevas, hora de la última lectura que el sensor puede borrar)."""
        sensor = self.sensores.buscar_por_codigo(codigo_sensor)
        if sensor is None or not sensor.esta_habilitado():
            log.warning("Lectura rechazada de %s", codigo_sensor)
            return 0, None
        if len(datos) > 1 and sensor.estado == EstadoSensor.SIN_SENAL:
            sensor.iniciar_sincronizacion()
        lote = self._leer(sensor.id, datos)
        if not lote:
            return 0, None
        insertadas = self.lecturas.guardar_lote(lote)
        hasta = max(l.medido_en for l in lote)
        sensor.registrar_lectura(hasta)
        if sensor.estado == EstadoSensor.SINCRONIZANDO:
            sensor.completar_sincronizacion()
        self.sensores.guardar(sensor)
        self._encolar_picos(lote, sensor.ubicacion.distrito, en_vivo=len(datos) == 1)
        return insertadas, hasta

    @staticmethod
    def _leer(sensor_id, datos: list[dict[str, Any]]) -> list[Lectura]:
        lote = (Lectura(sensor_id=sensor_id, pm10=Decimal(str(d["pm10"])), pm25=Decimal(str(d["pm25"])),
                        medido_en=datetime.fromisoformat(d["medido_en"])) for d in datos)
        return [l for l in lote if l.es_valida()]

    def _encolar_picos(self, lote: list[Lectura], distrito: str, en_vivo: bool) -> None:
        """Un mensaje de una sola lectura es en vivo aunque el reloj del sensor esté atrasado (R6)."""
        limite = self.reloj() - VENTANA_ALERTA_PUBLICA
        picos = [l for l in lote if l.supera_umbral(UMBRAL_PM10)]
        frescas = [l for l in picos if en_vivo or l.medido_en >= limite]
        self._encolar(self.encolar_alerta, frescas, distrito)
        self._encolar(self.encolar_historico, [l for l in picos if l not in frescas], distrito)

    @staticmethod
    def _encolar(destino: EncolarPico | None, lecturas: list[Lectura], distrito: str) -> None:
        if destino is not None and lecturas:
            destino(max(lecturas, key=lambda l: l.pm10), distrito)
