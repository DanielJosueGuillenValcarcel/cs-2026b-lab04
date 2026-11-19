"""E7: compara 3 ejecuciones nuevas del mejor prompt (criterios v3) sobre H1, H7 y H9.

Uso: python prompts/no_determinismo.py
"""
import difflib
import json
import sys
from itertools import combinations
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "criterios"))
import asserts  # noqa: E402

CASOS = {c["vars"]["id"]: c for c in yaml.safe_load((RAIZ / "criterios/casos.yaml").read_text(encoding="utf-8"))}


def pasa(texto, caso):
    if caso["vars"]["esperado"] == "no_invest":
        return asserts.a4_rechaza_no_invest(texto, caso)["pass"]
    return asserts.a2_exito_y_error(texto, caso)["pass"] and asserts.a3_sin_implementacion(texto, caso)["pass"]


def main():
    print("| Caso | Corrida | invest_ok | Escenarios (tipos) | Preguntas | Caracteres | ¿Pasa? |")
    print("|---|:---:|:---:|---|:---:|:---:|:---:|")
    for caso in ("H1", "H7", "H9"):
        textos = [(RAIZ / f"criterios/no-determinismo/corrida-{n}/{caso}.txt").read_text(encoding="utf-8")
                  for n in (1, 2, 3)]
        for n, t in enumerate(textos, 1):
            d = json.loads(t)
            tipos = ", ".join(e["tipo"] for e in d["escenarios"]) or "—"
            print(f"| {caso} | {n} | {d['invest_ok']} | {tipos} | {len(d['preguntas'])} | {len(t)} "
                  f"| {'Sí' if pasa(t, CASOS[caso]) else 'No'} |")
        sims = [difflib.SequenceMatcher(None, a, b).ratio() for a, b in combinations(textos, 2)]
        print(f"| {caso} | similitud | {min(sims):.2f} a {max(sims):.2f} | | | | |")


if __name__ == "__main__":
    main()
