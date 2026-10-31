"""Experimentos reales con Mosquitto 2.0 (ADR-007 y ADR-008).

Levanta un broker local con la configuración de infra/mosquitto/ (sin TLS, en un puerto libre)
y mide lo que pasa con las lecturas cuando la ingesta o el broker se caen, y si la ACL impide
que un sensor publique en el tema de otro. Requiere el ejecutable `mosquitto` y paho-mqtt.
"""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import paho.mqtt.client as mqtt

RAIZ = Path(__file__).resolve().parent.parent
CONF_PRODUCCION = RAIZ / "infra" / "mosquitto" / "mosquitto.conf"
ACL_PRODUCCION = RAIZ / "infra" / "mosquitto" / "acl"
CLAVES_EXCLUIDAS = ("listener", "cafile", "certfile", "keyfile", "password_file", "acl_file",
                    "persistence_location", "allow_anonymous")


def disponible() -> bool:
    return shutil.which("mosquitto") is not None


def ajustes_produccion() -> list[str]:
    lineas = []
    for l in CONF_PRODUCCION.read_text().splitlines():
        l = l.strip()
        if l and not l.startswith("#") and not l.startswith(CLAVES_EXCLUIDAS):
            lineas.append(l)
    return lineas


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Broker:
    def __init__(self, ajustes: list[str], usuarios: dict[str, str] | None = None, acl: str | None = None):
        self.dir = Path(tempfile.mkdtemp(prefix="mosq-"))
        self.puerto = _puerto_libre()
        conf = [f"listener {self.puerto} 127.0.0.1", f"persistence_location {self.dir}/", *ajustes]
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            conf.append("user root")
        if usuarios is None:
            conf.append("allow_anonymous true")
        else:
            pw = self.dir / "passwd"
            pw.write_text("")
            os.chmod(pw, 0o600)
            for u, c in usuarios.items():
                subprocess.run(["mosquitto_passwd", "-b", str(pw), u, c], check=True, capture_output=True)
            os.chmod(pw, 0o600)
            conf += ["allow_anonymous false", f"password_file {pw}"]
            if acl is not None:
                (self.dir / "acl").write_text(acl)
                os.chmod(self.dir / "acl", 0o600)
                conf.append(f"acl_file {self.dir / 'acl'}")
        (self.dir / "mosquitto.conf").write_text("\n".join(conf) + "\n")
        self.proc = None

    def iniciar(self):
        self.proc = subprocess.Popen(["mosquitto", "-c", str(self.dir / "mosquitto.conf")],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", self.puerto), timeout=0.1).close()
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("Mosquitto no inició")

    def matar(self):
        self.proc.send_signal(signal.SIGKILL)
        self.proc.wait()

    def detener(self):
        self.proc.terminate()
        self.proc.wait()

    def recargar(self):
        self.proc.send_signal(signal.SIGHUP)

    def limpiar(self):
        if self.proc and self.proc.poll() is None:
            self.detener()
        shutil.rmtree(self.dir, ignore_errors=True)


@contextmanager
def broker(ajustes, usuarios=None, acl=None):
    b = Broker(ajustes, usuarios, acl).iniciar()
    try:
        yield b
    finally:
        b.limpiar()


def _cliente(b: Broker, client_id: str, usuario=None, clave=None, limpia=True, al_mensaje=None):
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=limpia)
    c.on_message = al_mensaje
    if usuario:
        c.username_pw_set(usuario, clave)
    resultado = {}
    conectado = threading.Event()

    def al_conectar(cl, ud, flags, rc, props):
        resultado["rc"] = rc
        conectado.set()

    c.on_connect = al_conectar
    c.connect("127.0.0.1", b.puerto)
    c.loop_start()
    conectado.wait(5)
    return c, resultado.get("rc")


class Ingesta:
    """Suscriptor con sesión persistente (clean_session=False, QoS 1), como en ADR-003."""

    def __init__(self, b: Broker, usuario=None, clave=None):
        self.b, self.usuario, self.clave = b, usuario, clave
        self.recibidas: list[tuple[str, bytes]] = []
        self.cliente = None

    def conectar(self):
        self.cliente, rc = _cliente(self.b, "ingesta", self.usuario, self.clave, limpia=False,
                                    al_mensaje=lambda c, u, m: self.recibidas.append((m.topic, m.payload)))
        self.cliente.subscribe("airemisti/+/lecturas", qos=1)
        time.sleep(0.2)
        return rc

    def desconectar(self):
        self.cliente.disconnect()
        self.cliente.loop_stop()

    def esperar(self, n, timeout=20):
        fin = time.time() + timeout
        ultimo, quieto = -1, time.time()
        while time.time() < fin and len(self.recibidas) < n:
            if len(self.recibidas) != ultimo:
                ultimo, quieto = len(self.recibidas), time.time()
            elif time.time() - quieto > 2:
                break
            time.sleep(0.05)
        return len(self.recibidas)


def publicar_minutos(b: Broker, sensores: int, minutos: int, publicadores: int = 8) -> int:
    """Publica `minutos` lecturas de cada sensor con QoS 1 (una por sensor y minuto)."""
    hilos, total = [], [0]
    candado = threading.Lock()

    def trabajo(k):
        c, _ = _cliente(b, f"simulador-{k}")
        n = 0
        for m in range(minutos):
            for s in range(k, sensores, publicadores):
                c.publish(f"airemisti/AQP-{s:04d}/lecturas", f'{{"minuto":{m}}}', qos=1).wait_for_publish(5)
                n += 1
        c.disconnect()
        c.loop_stop()
        with candado:
            total[0] += n

    for k in range(publicadores):
        h = threading.Thread(target=trabajo, args=(k,))
        h.start()
        hilos.append(h)
    for h in hilos:
        h.join()
    return total[0]


def experimento_caida_ingesta(ajustes, sensores=400, minutos=10) -> dict:
    """QA-03: la ingesta se cae `minutos`; el broker debe retener todas las lecturas."""
    with broker(ajustes) as b:
        ing = Ingesta(b)
        ing.conectar()
        ing.desconectar()
        enviadas = publicar_minutos(b, sensores, minutos)
        ing.conectar()
        recibidas = ing.esperar(enviadas)
        ing.desconectar()
    return {"enviadas": enviadas, "recibidas": recibidas, "perdidas": enviadas - recibidas}


def experimento_caida_broker(ajustes, sensores=400, minutos=2) -> dict:
    """Caída brusca del broker (kill -9) con la ingesta desconectada."""
    with broker(ajustes) as b:
        ing = Ingesta(b)
        ing.conectar()
        ing.desconectar()
        enviadas = publicar_minutos(b, sensores, minutos)
        time.sleep(1.5)
        b.matar()
        b.iniciar()
        ing.conectar()
        recibidas = ing.esperar(enviadas, timeout=10)
        ing.desconectar()
    return {"enviadas": enviadas, "recibidas": recibidas, "perdidas": enviadas - recibidas}


def experimento_rendimiento(ajustes, mensajes=4000) -> dict:
    """Mensajes por segundo que acepta el broker con QoS 1 (para medir el costo de persistir)."""
    with broker(ajustes) as b:
        ing = Ingesta(b)
        ing.conectar()
        ing.desconectar()
        t0 = time.perf_counter()
        n = publicar_minutos(b, mensajes // 10, 10)
        dt = time.perf_counter() - t0
    return {"mensajes": n, "segundos": dt, "mensajes_por_s": n / dt}


def experimento_acl(sensores=("AQP-0001", "AQP-0002")) -> dict:
    """QA-04 y QA-06 con la ACL real de infra/mosquitto/acl."""
    usuarios = {s: f"clave-{s}" for s in sensores}
    usuarios["ingesta"] = "clave-ingesta"
    with broker(ajustes_produccion(), usuarios, ACL_PRODUCCION.read_text()) as b:
        ing = Ingesta(b, "ingesta", "clave-ingesta")
        ing.conectar()
        a, b_ = sensores[0], sensores[1]
        c, _ = _cliente(b, a, a, usuarios[a])
        c.publish(f"airemisti/{a}/lecturas", b"propia", qos=1).wait_for_publish(5)
        c.publish(f"airemisti/{b_}/lecturas", b"suplantada", qos=1).wait_for_publish(5)
        c.publish("airemisti/todos/lecturas", b"inventada", qos=1).wait_for_publish(5)
        time.sleep(1)
        anonimo = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="intruso")
        rc_anonimo = {}
        anonimo.on_connect = lambda cl, ud, fl, rc, pr: rc_anonimo.setdefault("rc", rc)
        anonimo.connect("127.0.0.1", b.puerto)
        anonimo.loop_start()
        time.sleep(1)
        anonimo.loop_stop()
        _, rc_mala = _cliente(b, "AQP-0001-bis", a, "clave-equivocada")
        c.disconnect()
        c.loop_stop()
        ing.desconectar()
    temas = [t for t, _ in ing.recibidas]
    return {"propias_aceptadas": temas.count(f"airemisti/{a}/lecturas"),
            "suplantaciones_aceptadas": len(temas) - temas.count(f"airemisti/{a}/lecturas"),
            "anonimo_rechazado": rc_anonimo.get("rc") is not None and rc_anonimo["rc"].is_failure,
            "clave_incorrecta_rechazada": rc_mala is not None and rc_mala.is_failure}


def experimento_acuse(ajustes, sensores=400, minutos=2, reenvio_s=3.0) -> dict:
    """ADR-007: el sensor borra una lectura de su microSD solo cuando recibe el acuse de la ingesta.

    La ingesta está caída, el broker acepta las lecturas (PUBACK) y muere con kill -9 antes de
    guardarlas en disco. Al volver, los sensores reenvían lo que no fue confirmado.
    """
    pendientes = {f"AQP-{s:04d}/{m}" for s in range(sensores) for m in range(minutos)}
    candado = threading.Lock()

    def al_acuse(c, u, m):
        with candado:
            pendientes.discard(m.payload.decode())

    with broker(ajustes) as b:
        ing = Ingesta(b)
        ing.conectar()
        ing.desconectar()
        sim, _ = _cliente(b, "simulador-sensores", al_mensaje=al_acuse)
        sim.subscribe("airemisti/+/ack", qos=1)
        for clave in sorted(pendientes):
            s, m = clave.split("/")
            sim.publish(f"airemisti/{s}/lecturas", clave, qos=1).wait_for_publish(5)
        sim.disconnect()
        sim.loop_stop()
        time.sleep(1.5)
        b.matar()
        b.iniciar()

        guardadas = set()
        acusador = {}

        def al_lectura(c, u, msg):
            clave = msg.payload.decode()
            guardadas.add(clave)                       # INSERT ... ON CONFLICT DO NOTHING
            c.publish(msg.topic.replace("/lecturas", "/ack"), clave, qos=1)

        acusador["c"], _ = _cliente(b, "ingesta", limpia=False, al_mensaje=al_lectura)
        acusador["c"].subscribe("airemisti/+/lecturas", qos=1)
        sim, _ = _cliente(b, "simulador-sensores", al_mensaje=al_acuse)
        sim.subscribe("airemisti/+/ack", qos=1)
        reenviadas = 0
        for _ in range(5):
            time.sleep(reenvio_s)
            with candado:
                faltan = sorted(pendientes)
            if not faltan:
                break
            for clave in faltan:
                s, _m = clave.split("/")
                sim.publish(f"airemisti/{s}/lecturas", clave, qos=1).wait_for_publish(5)
                reenviadas += 1
        time.sleep(reenvio_s)
        sim.disconnect()
        sim.loop_stop()
        acusador["c"].disconnect()
        acusador["c"].loop_stop()
    total = sensores * minutos
    return {"enviadas": total, "reenviadas": reenviadas, "guardadas": len(guardadas),
            "perdidas": total - len(guardadas), "sin_confirmar": len(pendientes)}


def experimento_alta_sensores(existentes=400, nuevos=50) -> dict:
    """QA-08: dar de alta sensores sin reiniciar el broker ni desconectar a la ingesta."""
    usuarios = {f"AQP-{i:04d}": f"clave-{i}" for i in range(existentes)}
    usuarios["ingesta"] = "clave-ingesta"
    with broker(ajustes_produccion(), usuarios, ACL_PRODUCCION.read_text()) as b:
        ing = Ingesta(b, "ingesta", "clave-ingesta")
        ing.conectar()
        desconexiones = []
        ing.cliente.on_disconnect = lambda *a: desconexiones.append(a)
        t0 = time.perf_counter()
        for i in range(existentes, existentes + nuevos):
            subprocess.run(["mosquitto_passwd", "-b", str(b.dir / "passwd"), f"AQP-{i:04d}", f"clave-{i}"],
                           check=True, capture_output=True)
        b.recargar()
        time.sleep(0.5)
        segundos = time.perf_counter() - t0
        aceptadas = 0
        for i in range(existentes, existentes + nuevos):
            c, rc = _cliente(b, f"AQP-{i:04d}", f"AQP-{i:04d}", f"clave-{i}")
            if rc is not None and not rc.is_failure:
                c.publish(f"airemisti/AQP-{i:04d}/lecturas", b"alta", qos=1).wait_for_publish(5)
                aceptadas += 1
            c.disconnect()
            c.loop_stop()
        recibidas = ing.esperar(nuevos, timeout=10)
        desconectada = bool(desconexiones)
        ing.desconectar()
    return {"nuevos": nuevos, "segundos_alta": segundos, "conectados": aceptadas,
            "lecturas_recibidas": recibidas, "ingesta_desconectada": desconectada}


DEFECTO = ["persistence true"]


if __name__ == "__main__":
    print("caída ingesta, valores por defecto:", experimento_caida_ingesta(DEFECTO))
    print("caída ingesta, infra/mosquitto:", experimento_caida_ingesta(ajustes_produccion()))
    print("ACL:", experimento_acl())
