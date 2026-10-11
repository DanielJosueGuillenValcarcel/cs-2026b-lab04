from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from airemisti.compartido.errores import TransicionInvalida


class EstadoSensor(Enum):
    ACTIVO = "ACTIVO"
    SIN_SENAL = "SIN_SENAL"
    SINCRONIZANDO = "SINCRONIZANDO"
    MANTENIMIENTO = "MANTENIMIENTO"
    BAJA = "BAJA"


@dataclass(frozen=True)
class Ubicacion:
    latitud: Decimal
    longitud: Decimal
    distrito: str


@dataclass
class Sensor:
    codigo: str
    ubicacion: Ubicacion
    estado: EstadoSensor | None = None
    ultima_lectura_en: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def _exigir(self, *permitidos: EstadoSensor) -> None:
        if self.estado not in permitidos:
            raise TransicionInvalida(f"{self.codigo}: no se permite desde {self.estado}")

    def dar_de_alta(self) -> None:
        self._exigir(None)
        self.estado = EstadoSensor.ACTIVO

    def registrar_lectura(self, medido_en: datetime) -> None:
        if self.ultima_lectura_en is None or medido_en > self.ultima_lectura_en:
            self.ultima_lectura_en = medido_en
        if self.estado == EstadoSensor.SIN_SENAL:
            self.estado = EstadoSensor.ACTIVO

    def marcar_sin_senal(self) -> None:
        self._exigir(EstadoSensor.ACTIVO)
        self.estado = EstadoSensor.SIN_SENAL

    def iniciar_sincronizacion(self) -> None:
        self._exigir(EstadoSensor.SIN_SENAL)
        self.estado = EstadoSensor.SINCRONIZANDO

    def completar_sincronizacion(self) -> None:
        self._exigir(EstadoSensor.SINCRONIZANDO)
        self.estado = EstadoSensor.ACTIVO

    def enviar_a_mantenimiento(self, motivo: str) -> None:
        self._exigir(EstadoSensor.ACTIVO, EstadoSensor.SIN_SENAL)
        self.estado = EstadoSensor.MANTENIMIENTO

    def reactivar(self) -> None:
        self._exigir(EstadoSensor.MANTENIMIENTO)
        self.estado = EstadoSensor.ACTIVO

    def dar_de_baja(self, motivo: str) -> None:
        self._exigir(EstadoSensor.MANTENIMIENTO, EstadoSensor.SIN_SENAL)
        self.estado = EstadoSensor.BAJA

    def esta_habilitado(self) -> bool:
        return self.estado in (
            EstadoSensor.ACTIVO,
            EstadoSensor.SIN_SENAL,
            EstadoSensor.SINCRONIZANDO,
        )


class RepositorioSensores(ABC):
    @abstractmethod
    def buscar_por_codigo(self, codigo: str) -> Sensor | None: ...

    @abstractmethod
    def guardar(self, s: Sensor) -> None: ...
