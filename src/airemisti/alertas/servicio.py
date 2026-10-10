from __future__ import annotations

from decimal import Decimal

from airemisti.alertas.dominio import Alerta, CanalAlertas, RepositorioAlertas
from airemisti.compartido.parametros import UMBRAL_PM10
from airemisti.lecturas.dominio import Lectura


class ServicioAlertas:
    def __init__(self, repositorio: RepositorioAlertas, canal: CanalAlertas,
                 umbral_pm10: Decimal = UMBRAL_PM10) -> None:
        self.repositorio = repositorio
        self.canal = canal
        self.umbral_pm10 = umbral_pm10

    def evaluar(self, lectura: Lectura, distrito: str) -> Alerta | None:
        if not lectura.supera_umbral(self.umbral_pm10):
            return None
        vigente = self.repositorio.alerta_activa(distrito)
        if vigente is not None:
            vigente.extender(lectura)
            self.repositorio.guardar(vigente)
            return vigente
        alerta = Alerta(distrito=distrito, lecturas=[lectura])
        self.repositorio.guardar(alerta)
        self.canal.publicar(alerta)
        return alerta
