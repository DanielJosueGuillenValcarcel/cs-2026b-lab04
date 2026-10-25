"""State: ciclo de vida del sensor (diagrama de estados del Lab 05).

Cada estado decide qué transiciones acepta. La clase base prohíbe todo,
así que una transición que no aparece en el diagrama falla sola.
"""
from __future__ import annotations


class TransicionInvalida(ValueError):
    pass


class EstadoSensor:
    nombre = "?"

    def _prohibido(self, accion):
        raise TransicionInvalida(f"No se puede {accion} un sensor {self.nombre}")

    def registrar_lectura(self, sensor):
        self._prohibido("registrar una lectura en")

    def marcar_sin_senal(self, sensor):
        self._prohibido("marcar sin señal")

    def iniciar_sincronizacion(self, sensor):
        self._prohibido("sincronizar")

    def completar_sincronizacion(self, sensor):
        self._prohibido("completar la sincronización de")

    def enviar_a_mantenimiento(self, sensor):
        self._prohibido("enviar a mantenimiento")

    def reactivar(self, sensor):
        self._prohibido("reactivar")

    def dar_de_baja(self, sensor):
        self._prohibido("dar de baja")


class Activo(EstadoSensor):
    nombre = "ACTIVO"

    def registrar_lectura(self, sensor):
        pass

    def marcar_sin_senal(self, sensor):
        sensor.cambiar_a(SinSenal())

    def enviar_a_mantenimiento(self, sensor):
        sensor.cambiar_a(Mantenimiento())


class SinSenal(EstadoSensor):
    nombre = "SIN_SENAL"

    def registrar_lectura(self, sensor):
        sensor.cambiar_a(Activo())

    def iniciar_sincronizacion(self, sensor):
        sensor.cambiar_a(Sincronizando())

    def enviar_a_mantenimiento(self, sensor):
        sensor.cambiar_a(Mantenimiento())

    def dar_de_baja(self, sensor):
        sensor.cambiar_a(Baja())


class Sincronizando(EstadoSensor):
    nombre = "SINCRONIZANDO"

    def completar_sincronizacion(self, sensor):
        sensor.cambiar_a(Activo())

    def marcar_sin_senal(self, sensor):
        sensor.cambiar_a(SinSenal())


class Mantenimiento(EstadoSensor):
    nombre = "MANTENIMIENTO"

    def reactivar(self, sensor):
        sensor.cambiar_a(Activo())

    def dar_de_baja(self, sensor):
        sensor.cambiar_a(Baja())


class Baja(EstadoSensor):
    nombre = "BAJA"


class Sensor:
    def __init__(self, codigo, distrito, marca, estado: EstadoSensor | None = None):
        self.codigo = codigo
        self.distrito = distrito
        self.marca = marca
        self._estado = estado or Activo()

    @property
    def estado(self) -> str:
        return self._estado.nombre

    def cambiar_a(self, estado: EstadoSensor):
        self._estado = estado

    def registrar_lectura(self):
        self._estado.registrar_lectura(self)

    def marcar_sin_senal(self):
        self._estado.marcar_sin_senal(self)

    def iniciar_sincronizacion(self):
        self._estado.iniciar_sincronizacion(self)

    def completar_sincronizacion(self):
        self._estado.completar_sincronizacion(self)

    def enviar_a_mantenimiento(self):
        self._estado.enviar_a_mantenimiento(self)

    def reactivar(self):
        self._estado.reactivar(self)

    def dar_de_baja(self):
        self._estado.dar_de_baja(self)
