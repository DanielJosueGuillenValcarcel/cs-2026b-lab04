from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from airemisti.alertas.dominio import CanalAlertas, RepositorioAlertas
from airemisti.alertas.servicio import ServicioAlertas
from airemisti.compartido.errores import TransicionInvalida
from airemisti.ingesta.servicio import ServicioIngesta
from airemisti.lecturas.dominio import RepositorioLecturas
from airemisti.sensores.dominio import EstadoSensor, RepositorioSensores, Sensor, Ubicacion


class SensoresMemoria(RepositorioSensores):
    def __init__(self, *sensores):
        self.datos = {s.codigo: s for s in sensores}

    def buscar_por_codigo(self, codigo):
        return self.datos.get(codigo)

    def guardar(self, s):
        self.datos[s.codigo] = s


class LecturasMemoria(RepositorioLecturas):
    def __init__(self):
        self.filas = {}

    def guardar_lote(self, lecturas):
        nuevas = 0
        for l in lecturas:
            clave = (l.sensor_id, l.medido_en)
            if clave not in self.filas:
                self.filas[clave] = l
                nuevas += 1
        return nuevas


class AlertasMemoria(RepositorioAlertas):
    def __init__(self):
        self.alertas = []

    def alerta_activa(self, distrito):
        ahora = datetime.now(timezone.utc)
        for a in self.alertas:
            if a.distrito == distrito and a.vigente_hasta >= ahora:
                return a
        return None

    def guardar(self, a):
        if a not in self.alertas:
            self.alertas.append(a)


class CanalFalso(CanalAlertas):
    def __init__(self):
        self.publicadas = []

    def publicar(self, a):
        self.publicadas.append(a)


def lectura(minutos_atras, pm10=40):
    t = datetime.now(timezone.utc) - timedelta(minutes=minutos_atras)
    return {"pm10": pm10, "pm25": 20, "medido_en": t.isoformat()}


@pytest.fixture
def entorno():
    sensor = Sensor("AQP-07", Ubicacion(Decimal("-16.39"), Decimal("-71.53"), "Cayma"))
    sensor.dar_de_alta()
    sensores, lecturas = SensoresMemoria(sensor), LecturasMemoria()
    canal, repo_alertas = CanalFalso(), AlertasMemoria()
    alertas = ServicioAlertas(repo_alertas, canal)
    ingesta = ServicioIngesta(sensores, lecturas, alertas.evaluar)
    return sensor, ingesta, lecturas, canal


def test_lectura_sobre_umbral_publica_alerta(entorno):
    sensor, ingesta, lecturas, canal = entorno
    assert ingesta.procesar_lote("AQP-07", [lectura(0, pm10=180)]) == 1
    assert len(canal.publicadas) == 1


def test_backlog_sin_perdidas_ni_duplicados(entorno):
    sensor, ingesta, lecturas, _ = entorno
    sensor.marcar_sin_senal()
    backlog = [lectura(m) for m in range(120, 0, -1)]
    assert ingesta.procesar_lote("AQP-07", backlog) == 120
    assert ingesta.procesar_lote("AQP-07", backlog) == 0
    assert len(lecturas.filas) == 120
    assert sensor.estado == EstadoSensor.ACTIVO


def test_alerta_vigente_no_se_repite(entorno):
    _, ingesta, _, canal = entorno
    ingesta.procesar_lote("AQP-07", [lectura(2, pm10=180)])
    ingesta.procesar_lote("AQP-07", [lectura(1, pm10=200)])
    assert len(canal.publicadas) == 1
    assert canal.publicadas[0].pm10_max == Decimal("200")


def test_alerta_retirada_publica_rectificacion(entorno):
    _, ingesta, _, canal = entorno
    ingesta.procesar_lote("AQP-07", [lectura(0, pm10=180)])
    alerta = canal.publicadas[0]
    assert alerta.mensaje().startswith("Alerta de calidad del aire en Cayma")
    alerta.retirar("lectura no plausible")
    assert alerta.mensaje().startswith("Rectificación")


def test_sensor_de_baja_se_rechaza(entorno):
    sensor, ingesta, lecturas, canal = entorno
    sensor.marcar_sin_senal()
    sensor.dar_de_baja("robado")
    assert ingesta.procesar_lote("AQP-07", [lectura(0, pm10=300)]) == 0
    assert not lecturas.filas and not canal.publicadas


def test_sensor_desconocido_se_rechaza(entorno):
    _, ingesta, _, canal = entorno
    assert ingesta.procesar_lote("FALSO-99", [lectura(0, pm10=300)]) == 0
    assert not canal.publicadas


TRANSICIONES = [
    ([], "dar_de_alta", EstadoSensor.ACTIVO),
    (["dar_de_alta"], "marcar_sin_senal", EstadoSensor.SIN_SENAL),
    (["dar_de_alta", "marcar_sin_senal"], "registrar_lectura", EstadoSensor.ACTIVO),
    (["dar_de_alta", "marcar_sin_senal"], "iniciar_sincronizacion", EstadoSensor.SINCRONIZANDO),
    (["dar_de_alta", "marcar_sin_senal", "iniciar_sincronizacion"], "completar_sincronizacion", EstadoSensor.ACTIVO),
    (["dar_de_alta"], "enviar_a_mantenimiento", EstadoSensor.MANTENIMIENTO),
    (["dar_de_alta", "marcar_sin_senal"], "enviar_a_mantenimiento", EstadoSensor.MANTENIMIENTO),
    (["dar_de_alta", "enviar_a_mantenimiento"], "reactivar", EstadoSensor.ACTIVO),
    (["dar_de_alta", "enviar_a_mantenimiento"], "dar_de_baja", EstadoSensor.BAJA),
    (["dar_de_alta", "marcar_sin_senal"], "dar_de_baja", EstadoSensor.BAJA),
]

ARGUMENTOS = {
    "registrar_lectura": (datetime.now(timezone.utc),),
    "enviar_a_mantenimiento": ("calibración",),
    "dar_de_baja": ("fin de vida útil",),
}


@pytest.mark.parametrize("previas,operacion,esperado", TRANSICIONES)
def test_transicion_del_diagrama_de_estados(previas, operacion, esperado):
    s = Sensor("AQP-01", Ubicacion(Decimal(0), Decimal(0), "Cercado"))
    for op in previas:
        getattr(s, op)(*ARGUMENTOS.get(op, ()))
    getattr(s, operacion)(*ARGUMENTOS.get(operacion, ()))
    assert s.estado == esperado


def test_transicion_no_modelada_se_rechaza():
    s = Sensor("AQP-01", Ubicacion(Decimal(0), Decimal(0), "Cercado"))
    s.dar_de_alta()
    with pytest.raises(TransicionInvalida):
        s.dar_de_baja("sin pasar por mantenimiento")
