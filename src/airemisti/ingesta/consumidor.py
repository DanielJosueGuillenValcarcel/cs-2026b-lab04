from __future__ import annotations

import json

from airemisti.ingesta.servicio import ServicioIngesta

TEMA = "airemisti/+/lecturas"


class ConsumidorMqtt:
    def __init__(self, servicio: ServicioIngesta, tema: str = TEMA) -> None:
        self.servicio = servicio
        self.tema = tema

    def al_recibir_mensaje(self, tema: str, payload: bytes) -> None:
        codigo = tema.split("/")[1]
        datos = json.loads(payload)
        if isinstance(datos, dict):
            datos = [datos]
        self.servicio.procesar_lote(codigo, datos)
