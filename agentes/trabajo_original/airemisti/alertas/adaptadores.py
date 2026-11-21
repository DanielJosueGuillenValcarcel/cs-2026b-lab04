from airemisti.alertas.dominio import Alerta, CanalAlertas


class TelegramAdapter(CanalAlertas):
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    def publicar(self, a: Alerta) -> None:
        raise NotImplementedError("Integrar con Telegram Bot API (sendMessage)")
