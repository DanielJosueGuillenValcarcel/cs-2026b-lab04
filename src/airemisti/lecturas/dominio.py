from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

PM_MAXIMO_FISICO = Decimal("1000")


@dataclass
class Lectura:
    sensor_id: UUID
    pm10: Decimal
    pm25: Decimal
    medido_en: datetime
    recibido_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None

    def es_valida(self) -> bool:
        en_rango = Decimal(0) <= self.pm25 <= self.pm10 <= PM_MAXIMO_FISICO
        return en_rango and self.medido_en <= self.recibido_en

    def supera_umbral(self, umbral: Decimal) -> bool:
        return self.pm10 > umbral


class RepositorioLecturas(ABC):
    @abstractmethod
    def guardar_lote(self, lecturas: list[Lectura]) -> int: ...
