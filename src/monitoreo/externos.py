from __future__ import annotations


def payload_airesense(pm10: float, pm25: float, medido_en: str) -> dict:
    return {"pm10": pm10, "pm25": pm25, "ts": medido_en}


def payload_purair(pm10: float, pm25: float, epoch: int) -> str:
    return f"PM10={round(pm10 * 10)};PM2_5={round(pm25 * 10)};T={epoch}"


class TelegramBotSimulado:
    def __init__(self, fallas: int = 0):
        self.fallas = fallas
        self.llamadas = 0
        self.enviados: list[tuple[str, str]] = []

    def send_message(self, chat_id: str, text: str) -> dict:
        self.llamadas += 1
        if self.llamadas <= self.fallas:
            raise ConnectionError("Telegram no responde")
        self.enviados.append((chat_id, text))
        return {"ok": True, "message_id": len(self.enviados)}


class ClienteOpenAISimulado:
    def __init__(self, respuesta: str):
        self.respuesta = respuesta
        self.llamadas = 0

    def chat_completions_create(self, model: str, messages: list[dict]) -> dict:
        self.llamadas += 1
        return {"choices": [{"message": {"role": "assistant", "content": self.respuesta}}]}


class _RespuestaGemini:
    def __init__(self, text: str):
        self.text = text


class ClienteGeminiSimulado:
    def __init__(self, respuesta: str):
        self.respuesta = respuesta
        self.llamadas = 0

    def generate_content(self, prompt: str) -> _RespuestaGemini:
        self.llamadas += 1
        return _RespuestaGemini(self.respuesta)
