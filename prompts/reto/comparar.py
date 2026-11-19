"""Reto A: tasa de aprobación, latencia y costo estimado por caso de la Tarea B v3 con dos modelos.

Uso: python prompts/evaluar.py prompts/alertas/promptfooconfig-reto.yaml && python prompts/reto/comparar.py
"""
import json
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETAS = {"claude-opus-5.5": RAIZ / "alertas/grabaciones/v3", "claude-haiku-5.5": RAIZ / "reto/grabaciones/haiku/v3"}
CARACTERES_POR_TOKEN = 3.5


def tokens(texto):
    return len(texto) / CARACTERES_POR_TOKEN


def main():
    datos = json.loads((RAIZ / "reto/latencias.json").read_text(encoding="utf-8"))
    resumen = json.loads((RAIZ / "alertas/evaluar-promptfooconfig-reto.json").read_text(encoding="utf-8"))["resumen"]
    filas = ["| Modelo | Aprobación | Latencia media (ms) | Latencia máx. (ms) | Tokens de salida (media) | Costo estimado por caso (USD) |",
             "|---|:---:|:---:|:---:|:---:|:---:|"]
    plantilla = (RAIZ / "alertas/v3.txt").read_text(encoding="utf-8")
    for modelo, carpeta in CARPETAS.items():
        r = resumen[f"{modelo} v3"]
        ms = list(datos["ms"][modelo].values())
        salidas = [tokens(f.read_text(encoding="utf-8")) for f in sorted(carpeta.glob("A*.txt"))]
        precio = datos["precios_usd_por_millon"][modelo]
        costo = (tokens(plantilla) * precio["entrada"] + statistics.mean(salidas) * precio["salida"]) / 1e6
        filas.append(f"| {modelo} | {r['aprobados']}/{r['total']} ({r['tasa']} %) | {statistics.mean(ms):.0f} | {max(ms)} "
                     f"| {statistics.mean(salidas):.0f} | {costo:.6f} |")
    print("\n".join(filas))


if __name__ == "__main__":
    main()
