"""Observabilidad: convierte las trazas JSONL de una corrida en un diagrama de secuencia (Mermaid) y en métricas.

Uso: python agente/traza.py trazas/issue02-multi
"""
import collections
import json
import pathlib
import re
import sys

ORDEN = ["planificador", "agente", "ejecutor", "revisor", "revisor_correccion", "revisor_diseno", "revisor_seguridad"]
ALIAS = {"planificador": ("PL", "Planificador"), "agente": ("AG", "Agente ReAct"), "ejecutor": ("EJ", "Ejecutor (actor)"),
         "revisor": ("RV", "Revisor (crítico)"), "revisor_correccion": ("RC", "Revisor de corrección"),
         "revisor_diseno": ("RD", "Revisor de diseño"), "revisor_seguridad": ("RS", "Revisor de seguridad")}


def cargar(carpeta):
    eventos = []
    for ronda in (1, 2, 3):
        for n in ORDEN:
            f = pathlib.Path(carpeta) / f"{n}{'' if ronda == 1 else f'_r{ronda}'}.jsonl"
            if f.exists():
                eventos += [dict(json.loads(l), ronda=ronda) for l in open(f, encoding="utf-8")]
    return eventos


def resumir(e) -> str:
    obs, acc, args = e["observacion"], e["accion"], e["args"]
    if acc == "leer_archivo":
        return f"contenido de {str(args.get('ruta', '')).split('/')[-1]}"
    if acc == "buscar":
        return "sin resultados" if "sin resultados" in obs else f"{len(obs.splitlines())} coincidencia(s)"
    if acc == "ver_cambios":
        return f"diff de {len(obs.splitlines())} líneas"
    if acc == "mapa_repo":
        return f"mapa de {sum(1 for l in obs.splitlines() if l.endswith(':'))} archivo(s)"
    if acc == "editar_archivo" and obs.startswith("OK"):
        return "OK, archivo modificado"
    resumen = [l.strip("= ") for l in obs.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    if not resumen and acc in ("ejecutar_pruebas", "ejecutar_comando"):
        return "salida de pytest (recortada)"
    return (resumen or obs.strip().splitlines() or [""])[-1].replace(";", ",").replace("#", "N.")[:40]


def a_mermaid(eventos) -> str:
    presentes = [n for n in ORDEN if any(e["agente"] == n for e in eventos)]
    l = ["sequenceDiagram", "    autonumber", "    actor U as Humano"]
    l += [f"    participant {ALIAS[n][0]} as {ALIAS[n][1]}" for n in presentes]
    l += ["    participant P as Política", "    participant H as Herramientas"]
    ronda_actual, primero = 1, presentes[0]
    for e in eventos:
        a = ALIAS[e["agente"]][0]
        if e["ronda"] != ronda_actual:
            ronda_actual = e["ronda"]
            l.append(f"    Note over {ALIAS[primero][0]},H: Ronda {ronda_actual} del bucle actor-crítico")
        if e["tipo"] == "objetivo":
            origen = "U" if e["agente"] in ("planificador", "agente") else ("PL" if e["agente"] == "ejecutor" else "EJ")
            l.append(f"    {origen}->>{a}: " + ("objetivo" if origen == "U" else "plan" if origen == "PL" else "resumen + diff"))
        elif e["tipo"] == "accion":
            if e["estado"] == "CONTRATO_INVALIDO":
                l.append(f"    Note right of {a}: contrato inválido")
            elif e["bloqueada"]:
                l += [f"    {a}-xP: {e['accion']}", f"    P--x{a}: BLOQUEADO"]
            else:
                l += [f"    {a}->>H: {e['accion']}", f"    H-->>{a}: {resumir(e)}"]
        elif e["tipo"] == "final" and e["agente"] not in ("planificador", "ejecutor"):
            texto = e["texto"].strip().splitlines()[0].split(".")[0].replace(";", ",").replace("#", "N.")[:60]
            l.append(f"    {a}-->>U: {texto}")
    return "\n".join(l)


def metricas(eventos) -> dict:
    m = collections.defaultdict(collections.Counter)
    for e in eventos:
        if e["tipo"] == "accion":
            clave = "contrato_invalido" if e["estado"] == "CONTRATO_INVALIDO" else ("bloqueadas" if e["bloqueada"] else "permitidas")
            m[e["agente"]][clave] += 1
            if e["accion"] != "(ninguna)":
                m[e["agente"]][e["accion"]] += 1
    return {k: dict(v) for k, v in m.items()}


if __name__ == "__main__":
    carpeta = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "trazas")
    ev = cargar(carpeta)
    (carpeta / "trayectoria.mmd").write_text(a_mermaid(ev), encoding="utf-8")
    print(json.dumps(metricas(ev), ensure_ascii=False, indent=1))
