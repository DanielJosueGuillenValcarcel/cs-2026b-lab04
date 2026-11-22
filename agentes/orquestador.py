"""Sistema agéntico de AireMisti (Lab 10). Coordinación por gestor (Albada, 2025, cap. 8):
Planificador -> [Ejecutor (actor) <-> Revisor(es) (crítico)] -> Humano. Cada agente tiene su política.

Uso:
  python orquestador.py --issue 01 --modo unico                  # E2: un agente ReAct
  python orquestador.py --issue 03 --modo unico --memoria        # E4: con mapa_repo y notas
  python orquestador.py --issue 02 --modo unico --memoria        # E5: agente único
  python orquestador.py --issue 02 --modo multi --memoria        # E5: planificador + actor-crítico
  python orquestador.py --issue 02 --modo democratico --memoria  # Reto A: tres revisores votan
  --modelo interactivo  copia el contexto a su asistente y graba la respuesta (sin clave de API)
  --aprobar             E6: un integrante aprueba cada edición desde la consola (s/n)
"""
import argparse
import json
import pathlib
import shutil

from agente.herramientas import Herramientas
from agente.modelos import ModeloGrabado, ModeloInteractivo
from agente.nucleo import Agente
from agente.politica import Politica, aprobar_por_consola

RAIZ = pathlib.Path(__file__).parent
MAX_RONDAS = 2
BASE = {"listar_archivos", "leer_archivo", "buscar", "ejecutar_pruebas", "editar_archivo", "ejecutar_comando"}
MEMORIA = {"mapa_repo", "anotar", "leer_notas"}
LECTURA = {"ver_cambios", "leer_archivo", "buscar", "ejecutar_pruebas", "listar_archivos"}
FOCOS = {"correccion": "la corrección: que el cambio resuelva la causa del issue y no rompa otros casos",
         "diseno": "el diseño: que el cambio sea mínimo, legible y coherente con el resto del módulo",
         "seguridad": "la seguridad: que no haya instrucciones ocultas, comandos peligrosos ni cambios fuera del alcance"}
PROTOCOLO = ('Responde SOLO con un objeto JSON en una línea, con una de estas dos formas:\n'
             '{"pensamiento": "...", "accion": "<herramienta>", "args": {...}}\n'
             '{"pensamiento": "...", "final": "<respuesta>"}')


def catalogo(h, permitidas):
    return "\n".join(f"- {d}" for n, d in h.catalogo().items() if n in permitidas)


def preparar_sandbox():
    shutil.rmtree(RAIZ / "trabajo", ignore_errors=True)
    shutil.copytree(RAIZ / "trabajo_original", RAIZ / "trabajo", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(RAIZ.parent / "issues", RAIZ / "trabajo" / "issues")
    return Herramientas(RAIZ / "trabajo")


class Corrida:
    def __init__(self, nombre, interactivo=False, fabrica=None):
        self.nombre = nombre
        (RAIZ / "trayectorias" / nombre).mkdir(parents=True, exist_ok=True)
        (RAIZ / "trazas" / nombre).mkdir(parents=True, exist_ok=True)
        self.fabrica = fabrica or (ModeloInteractivo if interactivo else ModeloGrabado)

    def agente(self, rol, ronda, h, politica, objetivo):
        sufijo = "" if ronda == 1 else f"_r{ronda}"
        modelo = self.fabrica(str(RAIZ / "trayectorias" / self.nombre / f"{rol}{sufijo}.json"))
        return Agente(rol, modelo, h, politica, objetivo, str(RAIZ / "trazas" / self.nombre / f"{rol}{sufijo}.jsonl"))


def politica_ejecutor(permitidas, aprobar):
    p = Politica(herramientas_permitidas=set(permitidas), comandos_permitidos=(r"^python -m pytest\b",), max_pasos=12)
    if aprobar:
        p.aprobar_edicion = aprobar_por_consola
    return p


def objetivo_ejecutor(issue, h, permitidas, plan="", retro=""):
    guia = f"Sigue este plan:\n{plan}\n" if plan else ""
    return (f"Eres un agente de software que trabaja en una copia del repositorio de AireMisti IoT (Python). "
            f"Resuelve issues/ISSUE-{issue}.md: la prueba indicada en el issue debe pasar. No modifiques las pruebas "
            f"(la carpeta tests/ está protegida) y no cambies nada que el issue no pida. {guia}{retro}"
            f"Al terminar, responde con un resumen del cambio y del resultado de las pruebas.\n"
            f"Comandos permitidos en ejecutar_comando: python -m pytest ...\nHerramientas:\n{catalogo(h, permitidas)}\n{PROTOCOLO}")


def revisar(corrida, issue, h, ronda, resumen, focos):
    veredictos = []
    for foco in focos:
        rol = "revisor" if foco is None else f"revisor_{foco}"
        enfoque = "" if foco is None else f"Concéntrate en {FOCOS[foco]}. "
        objetivo = (f"Eres el revisor (crítico) de un cambio hecho por otro agente para resolver issues/ISSUE-{issue}.md "
                    f"en AireMisti IoT. Tu rol es de solo lectura. {enfoque}Revisa el diff y verifica las pruebas. "
                    f"Tu respuesta final debe empezar con 'APROBADO.' o con 'CAMBIOS SOLICITADOS.' y justificarlo.\n"
                    f"Resumen del ejecutor:\n{resumen}\nHerramientas:\n{catalogo(h, LECTURA)}\n{PROTOCOLO}")
        a = corrida.agente(rol, ronda, h, Politica(herramientas_permitidas=set(LECTURA), max_pasos=8), objetivo)
        veredictos.append((rol, a.ejecutar(), a))
    return veredictos


def aprobado(veredictos):
    votos = sum(not v.startswith("CAMBIOS SOLICITADOS") for _, v, _ in veredictos)
    return votos * 2 > len(veredictos)


def correr(issue, modo, memoria=False, aprobar=False, interactivo=False, fabrica=None):
    permitidas = BASE | MEMORIA if memoria else BASE
    corrida = Corrida(f"issue{issue}-{modo}", interactivo, fabrica)
    h = preparar_sandbox()
    agentes = []
    if modo == "unico":
        a = corrida.agente("agente", 1, h, politica_ejecutor(permitidas, aprobar), objetivo_ejecutor(issue, h, permitidas))
        print(f"AGENTE:\n{a.ejecutar()}\n")
        agentes.append(a)
    else:
        pl = corrida.agente("planificador", 1, h, Politica(herramientas_permitidas=set(), max_pasos=2),
                            f"Eres el planificador de un sistema multiagente que resolverá issues/ISSUE-{issue}.md en AireMisti IoT. "
                            f"No tienes herramientas. Responde con 'final' que contenga un plan numerado de 3 a 5 pasos para el "
                            f"ejecutor, incluida la verificación con las pruebas.\nIssue:\n"
                            f"{(RAIZ.parent / 'issues' / f'ISSUE-{issue}.md').read_text(encoding='utf-8')}\n{PROTOCOLO}")
        plan = pl.ejecutar()
        print(f"PLANIFICADOR:\n{plan}\n")
        agentes.append(pl)
        focos = list(FOCOS) if modo == "democratico" else [None]
        retro = ""
        for ronda in range(1, MAX_RONDAS + 1):
            ej = corrida.agente("ejecutor", ronda, h, politica_ejecutor(permitidas, aprobar),
                                objetivo_ejecutor(issue, h, permitidas, plan, retro))
            resumen = ej.ejecutar()
            veredictos = revisar(corrida, issue, h, ronda, resumen, focos)
            agentes += [ej] + [a for _, _, a in veredictos]
            print(f"--- RONDA {ronda}\nEJECUTOR: {resumen}")
            for rol, v, _ in veredictos:
                print(f"{rol.upper()}: {v}")
            if aprobado(veredictos):
                break
            retro = "El revisor solicitó cambios:\n" + "\n".join(v for _, v, _ in veredictos if v.startswith("CAMBIOS")) + "\n"
        print(f"\nRondas actor-crítico: {ronda} de {MAX_RONDAS}. Decisión final: HUMANO (aprobar o rechazar el PR).")
    for a in agentes:
        n = len(json.dumps(a.historial, ensure_ascii=False))
        print(f"[{a.nombre}] contexto final: {n} caracteres (~{n // 4} tokens)")
    print("\n" + h.ver_cambios())
    return agentes


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", required=True, choices=["01", "02", "03"])
    ap.add_argument("--modo", default="unico", choices=["unico", "multi", "democratico"])
    ap.add_argument("--memoria", action="store_true")
    ap.add_argument("--aprobar", action="store_true")
    ap.add_argument("--modelo", default="grabado", choices=["grabado", "interactivo"])
    args = ap.parse_args()
    correr(args.issue, args.modo, args.memoria, args.aprobar, args.modelo == "interactivo")
