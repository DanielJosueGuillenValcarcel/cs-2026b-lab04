"""Etapa E2: lectura de sensores y norma de calidad con Adapter + Factory + Strategy."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from monitoreo.externos import TelegramBotSimulado
from monitoreo.indices import FabricaNormas
from monitoreo.sensores import FabricaLectores, Lectura, LecturaDescartada

CHAT_ALERTAS = "@airemisti_alertas"


@dataclass
class Sensor:
    codigo: str
    distrito: str
    marca: str
    estado: str = "ACTIVO"

    def marcar_sin_senal(self):
        if self.estado == "ACTIVO":
            self.estado = "SIN_SENAL"
        else:
            raise ValueError(f"No se puede marcar sin señal un sensor {self.estado}")

    def enviar_a_mantenimiento(self):
        if self.estado == "ACTIVO" or self.estado == "SIN_SENAL":
            self.estado = "MANTENIMIENTO"
        else:
            raise ValueError(f"No se puede enviar a mantenimiento un sensor {self.estado}")

    def dar_de_baja(self):
        if self.estado == "MANTENIMIENTO" or self.estado == "SIN_SENAL":
            self.estado = "BAJA"
        else:
            raise ValueError(f"No se puede dar de baja un sensor {self.estado}")


@dataclass
class Alerta:
    distrito: str
    pm10_max: float
    vigente_hasta: datetime
    lecturas: int = 1


class ServicioMonitoreo:
    def __init__(self, telegram=None, norma="ECA", *, lectores=None, normas=None):
        self.telegram = telegram or TelegramBotSimulado()
        self.lectores = lectores or FabricaLectores()
        self.norma = (normas or FabricaNormas()).crear(norma)
        self.sensores, self.lecturas, self.alertas, self.eventos = {}, {}, {}, []

    def registrar_sensor(self, sensor):
        self.sensores[sensor.codigo] = sensor

    def procesar(self, codigo, payload):
        sensor = self.sensores.get(codigo)
        if sensor is None:
            raise ValueError(f"Sensor no registrado: {codigo}")
        if sensor.estado == "BAJA":
            raise ValueError(f"El sensor {codigo} está dado de baja")
        elif sensor.estado == "MANTENIMIENTO":
            raise ValueError(f"El sensor {codigo} está en mantenimiento")
        lector = self.lectores.crear(sensor.marca)
        try:
            lectura = lector.leer(codigo, payload)
        except LecturaDescartada:
            return "DESCARTADA"
        if sensor.estado == "SIN_SENAL":
            sensor.estado = "ACTIVO"
        clave = (codigo, lectura.medido_en)
        if clave in self.lecturas:
            return "DUPLICADA"
        self.lecturas[clave] = lectura
        self.eventos.append(f"mapa:{codigo}:{self.norma.clasificar(lectura)}")
        pm10, medido_en = lectura.pm10, lectura.medido_en
        if pm10 > 150:
            alerta = self.alertas.get(sensor.distrito)
            if alerta is not None and medido_en <= alerta.vigente_hasta:
                alerta.pm10_max = max(alerta.pm10_max, pm10)
                alerta.vigente_hasta = medido_en + timedelta(hours=1)
                alerta.lecturas += 1
            else:
                alerta = Alerta(sensor.distrito, pm10, medido_en + timedelta(hours=1))
                self.alertas[sensor.distrito] = alerta
                texto = f"Alerta de calidad del aire en {sensor.distrito}: PM10 = {pm10:.1f} µg/m³."
                enviado = False
                for intento in range(3):
                    try:
                        self.telegram.send_message(CHAT_ALERTAS, texto)
                        enviado = True
                        break
                    except ConnectionError:
                        if intento == 2:
                            enviado = False
                if enviado:
                    self.eventos.append(f"telegram:{texto}")
                else:
                    self.eventos.append(f"telegram_fallido:{sensor.distrito}")
                self.eventos.append(f"analista:{sensor.distrito}:{pm10:.1f}")
        return "GUARDADA"

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
