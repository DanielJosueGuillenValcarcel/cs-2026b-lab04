"""Etapa E4: Observer para los avisos y Decorator para los reintentos de Telegram.

La API pública es la misma que monitoreo.antes.servicio, así las pruebas de
caracterización corren sobre las dos versiones.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

from monitoreo.estados import Sensor
from monitoreo.eventos import (AvisoAnalista, ConReintentos, MapaPublico, NotificadorTelegram,
                               PublicadorEventos, TelegramAdapter)
from monitoreo.externos import TelegramBotSimulado
from monitoreo.indices import FabricaNormas
from monitoreo.sensores import FabricaLectores, Lectura, LecturaDescartada

__all__ = ["Alerta", "Lectura", "Sensor", "ServicioMonitoreo"]

UMBRAL_ALERTA_PM10 = 150
VIGENCIA_ALERTA = timedelta(hours=1)


@dataclass
class Alerta:
    distrito: str
    pm10_max: float
    vigente_hasta: object
    lecturas: int = 1

    def vigente(self, momento) -> bool:
        return momento <= self.vigente_hasta

    def extender(self, lectura):
        self.pm10_max = max(self.pm10_max, lectura.pm10)
        self.vigente_hasta = lectura.medido_en + VIGENCIA_ALERTA
        self.lecturas += 1


class ServicioMonitoreo:
    def __init__(self, telegram=None, norma="ECA", *, lectores=None, normas=None, publicador=None):
        self.lectores = lectores or FabricaLectores()
        self.norma = (normas or FabricaNormas()).crear(norma)
        self.sensores, self.lecturas, self.alertas, self.eventos = {}, {}, {}, []
        self.publicador = publicador or self._publicador_por_defecto(telegram or TelegramBotSimulado())

    def _publicador_por_defecto(self, bot):
        p = PublicadorEventos()
        p.suscribir(MapaPublico(self.eventos))
        p.suscribir(NotificadorTelegram(ConReintentos(TelegramAdapter(bot)), self.eventos))
        p.suscribir(AvisoAnalista(self.eventos))
        return p

    def registrar_sensor(self, sensor):
        self.sensores[sensor.codigo] = sensor

    def procesar(self, codigo, payload):
        sensor = self.sensores.get(codigo)
        if sensor is None:
            raise ValueError(f"Sensor no registrado: {codigo}")
        lector = self.lectores.crear(sensor.marca)
        try:
            lectura = lector.leer(codigo, payload)
        except LecturaDescartada:
            sensor.registrar_lectura()  # el sensor sí respondió; su estado decide si se acepta
            return "DESCARTADA"
        sensor.registrar_lectura()
        clave = (codigo, lectura.medido_en)
        if clave in self.lecturas:
            return "DUPLICADA"
        self.lecturas[clave] = lectura
        self.publicador.lectura_guardada(lectura, self.norma.clasificar(lectura))
        if lectura.pm10 > UMBRAL_ALERTA_PM10:
            self._actualizar_alerta(sensor.distrito, lectura)
        return "GUARDADA"

    def _actualizar_alerta(self, distrito, lectura):
        alerta = self.alertas.get(distrito)
        if alerta is not None and alerta.vigente(lectura.medido_en):
            alerta.extender(lectura)
            return
        alerta = Alerta(distrito, lectura.pm10, lectura.medido_en + VIGENCIA_ALERTA)
        self.alertas[distrito] = alerta
        self.publicador.alerta_abierta(alerta)

    def explicar_alerta(self, distrito, proveedor, cliente):
        alerta = self.alertas[distrito]
        prompt = (f"Explica en lenguaje sencillo, en menos de 60 palabras, que en {distrito} "
                  f"el PM10 llegó a {alerta.pm10_max:.1f} µg/m³ y qué precauciones tomar.")
        if proveedor == "OPENAI":
            r = cliente.chat_completions_create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
            texto = r["choices"][0]["message"]["content"]
        elif proveedor == "GEMINI":
            texto = cliente.generate_content(prompt).text
        else:
            raise ValueError(f"Proveedor de IA no soportado: {proveedor}")
        for valor in re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:µg/m³|ug/m3)", texto):
            if abs(float(valor.replace(",", ".")) - alerta.pm10_max) > 0.05:
                raise ValueError(f"Guardrail: la IA inventó un valor de PM10 ({valor})")
        for palabra in ["diagnóstico", "medicamento", "tratamiento", "cura"]:
            if palabra in texto.lower():
                raise ValueError(f"Guardrail: consejo médico no permitido ('{palabra}')")
        if len(texto) > 400:
            raise ValueError("Guardrail: la explicación es demasiado larga para Telegram")
        return texto
