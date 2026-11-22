from __future__ import annotations

import json
from typing import Callable

from airemisti.ingesta.servicio import ServicioIngesta

TEMA = "airemisti/+/lecturas"


class ConsumidorMqtt:
    """Adaptador MQTT de la ingesta.

    Después de guardar el lote publica un acuse en airemisti/<sensor>/ack con la hora de la última
    lectura guardada; el sensor solo borra de su microSD lo confirmado (ADR-007).
    """

    def __init__(self, servicio: ServicioIngesta, tema: str = TEMA,
                 publicar: Callable[[str, str], None] | None = None) -> None:
        self.servicio = servicio
        self.tema = tema
        self.publicar = publicar

    def al_recibir_mensaje(self, tema: str, payload: bytes) -> None:
        codigo = tema.split("/")[1]
        datos = json.loads(payload)
        if isinstance(datos, dict):
            datos = [datos]
        _, hasta = self.servicio.procesar(codigo, datos)
        if hasta is not None and self.publicar is not None:
            self.publicar(f"airemisti/{codigo}/ack", hasta.isoformat())
