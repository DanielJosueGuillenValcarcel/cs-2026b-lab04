"""Guardrails: qué puede hacer el agente, cuántas veces y con qué aprobación."""
import re
from dataclasses import dataclass, field


@dataclass
class Decision:
    permitido: bool
    motivo: str = ""


@dataclass
class Politica:
    herramientas_permitidas: set = field(default_factory=lambda: {
        "listar_archivos", "leer_archivo", "buscar", "ejecutar_pruebas", "editar_archivo", "ejecutar_comando"})
    comandos_permitidos: tuple = (r"^python -m pytest\b", r"^radon cc\b", r"^lint-imports\b", r"^git (status|diff)\b")
    rutas_protegidas: tuple = ("tests/",)          # el agente no puede "arreglar" las pruebas para que pasen
    max_pasos: int = 15
    aprobar_edicion = None                          # función opcional: humano en el circuito (human-in-the-loop)

    def evaluar(self, accion: str, args: dict, paso: int) -> Decision:
        if paso > self.max_pasos:
            return Decision(False, f"Se alcanzó el máximo de {self.max_pasos} pasos")
        if accion not in self.herramientas_permitidas:
            return Decision(False, f"Herramienta no permitida: {accion}")
        if accion == "ejecutar_comando":
            cmd = args.get("comando", "")
            if not any(re.search(p, cmd) for p in self.comandos_permitidos):
                return Decision(False, f"Comando fuera de la lista permitida: {cmd!r}")
        if accion == "editar_archivo":
            ruta = args.get("ruta", "")
            if ruta.startswith(self.rutas_protegidas):
                return Decision(False, f"Ruta protegida: {ruta}")
            if self.aprobar_edicion and not self.aprobar_edicion(args):
                return Decision(False, "El revisor humano rechazó la edición")
        return Decision(True)


def aprobar_por_consola(args: dict, entrada=input, salida=print) -> bool:
    """Humano en el circuito (E6): muestra la edición propuesta y acepta solo 's' o 'n'."""
    salida(f"\n¿Aprobar la edición de {args.get('ruta')}?\n--- antes ---\n{args.get('antes')}\n--- después ---\n{args.get('despues')}")
    while True:
        respuesta = entrada("Responda s o n: ").strip().lower()
        if respuesta in ("s", "n"):
            return respuesta == "s"
        salida("Respuesta no válida: escriba solo 's' (sí) o 'n' (no).")
