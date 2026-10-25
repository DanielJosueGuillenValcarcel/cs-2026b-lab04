"""Observer para avisar cuando se guarda una lectura o se abre una alerta.

El canal de Telegram va detrás de un Adapter y los reintentos son un Decorator.
"""
from __future__ import annotations

from typing import Protocol

CHAT_ALERTAS = "@airemisti_alertas"


class CanalAlertas(Protocol):
    def enviar(self, texto: str) -> None: ...


class TelegramAdapter:
    def __init__(self, bot, chat_id: str = CHAT_ALERTAS):
        self.bot = bot
        self.chat_id = chat_id

    def enviar(self, texto):
        self.bot.send_message(self.chat_id, texto)


class ConReintentos:
    """Decorator: reintenta solo ante ConnectionError, otros errores pasan."""

    def __init__(self, canal: CanalAlertas, intentos: int = 3):
        self.canal = canal
        self.intentos = intentos

    def enviar(self, texto):
        for intento in range(1, self.intentos + 1):
            try:
                return self.canal.enviar(texto)
            except ConnectionError:
                if intento == self.intentos:
                    raise


class Suscriptor(Protocol):
    def lectura_guardada(self, lectura, nivel: str) -> None: ...
    def alerta_abierta(self, alerta) -> None: ...


class PublicadorEventos:
    def __init__(self):
        self._suscriptores: list[Suscriptor] = []

    def suscribir(self, s: Suscriptor):
        self._suscriptores.append(s)

    def lectura_guardada(self, lectura, nivel):
        for s in self._suscriptores:
            s.lectura_guardada(lectura, nivel)

    def alerta_abierta(self, alerta):
        for s in self._suscriptores:
            s.alerta_abierta(alerta)


class SuscriptorBase:
    def lectura_guardada(self, lectura, nivel):
        pass

    def alerta_abierta(self, alerta):
        pass


class MapaPublico(SuscriptorBase):
    def __init__(self, bitacora: list):
        self.bitacora = bitacora

    def lectura_guardada(self, lectura, nivel):
        self.bitacora.append(f"mapa:{lectura.codigo}:{nivel}")


class NotificadorTelegram(SuscriptorBase):
    def __init__(self, canal: CanalAlertas, bitacora: list):
        self.canal = canal
        self.bitacora = bitacora

    def alerta_abierta(self, alerta):
        texto = f"Alerta de calidad del aire en {alerta.distrito}: PM10 = {alerta.pm10_max:.1f} µg/m³."
        try:
            self.canal.enviar(texto)
            self.bitacora.append(f"telegram:{texto}")
        except ConnectionError:
            self.bitacora.append(f"telegram_fallido:{alerta.distrito}")


class AvisoAnalista(SuscriptorBase):
    def __init__(self, bitacora: list):
        self.bitacora = bitacora

    def alerta_abierta(self, alerta):
        self.bitacora.append(f"analista:{alerta.distrito}:{alerta.pm10_max:.1f}")
