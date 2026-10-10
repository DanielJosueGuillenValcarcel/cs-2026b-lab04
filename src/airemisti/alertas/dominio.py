from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from airemisti.compartido.errores import TransicionInvalida
from airemisti.compartido.parametros import UMBRAL_PM10
from airemisti.lecturas.dominio import Lectura

VIGENCIA = timedelta(hours=1)


class EstadoAlerta(Enum):
    EMITIDA = "EMITIDA"
    CONFIRMADA = "CONFIRMADA"
    RETIRADA = "RETIRADA"


@dataclass
class Alerta:
    distrito: str
    lecturas: list[Lectura]
    pm10_max: Decimal = Decimal(0)
    emitida_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    vigente_hasta: datetime | None = None
    estado: EstadoAlerta = EstadoAlerta.EMITIDA
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.lecturas:
            raise ValueError("Una alerta necesita al menos una lectura (1..*)")
        self.pm10_max = max(l.pm10 for l in self.lecturas)
        self.vigente_hasta = self.emitida_en + VIGENCIA

    def extender(self, lectura: Lectura) -> None:
        self.lecturas.append(lectura)
        self.pm10_max = max(self.pm10_max, lectura.pm10)
        self.vigente_hasta = lectura.medido_en + VIGENCIA

    def confirmar(self) -> None:
        if self.estado != EstadoAlerta.EMITIDA:
            raise TransicionInvalida("Solo se confirma una alerta emitida")
        self.estado = EstadoAlerta.CONFIRMADA

    def retirar(self, motivo: str) -> None:
        if self.estado == EstadoAlerta.RETIRADA:
            raise TransicionInvalida("La alerta ya fue retirada")
        self.estado = EstadoAlerta.RETIRADA

    def mensaje(self) -> str:
        if self.estado == EstadoAlerta.RETIRADA:
            return (
                f"Rectificación: se retira la alerta de calidad del aire en {self.distrito}. "
                f"La lectura de PM10 = {self.pm10_max} µg/m³ no fue confirmada."
            )
        return (
            f"Alerta de calidad del aire en {self.distrito}: "
            f"PM10 = {self.pm10_max} µg/m³ (umbral {UMBRAL_PM10}). Evite actividades al aire libre."
        )


class RepositorioAlertas(ABC):
    @abstractmethod
    def alerta_activa(self, distrito: str) -> Alerta | None: ...

    @abstractmethod
    def guardar(self, a: Alerta) -> None: ...


class CanalAlertas(ABC):
    @abstractmethod
    def publicar(self, a: Alerta) -> None: ...
