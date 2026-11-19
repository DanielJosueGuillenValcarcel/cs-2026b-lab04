"""Gráficos del README del Lab 09 a partir de los resultados del evaluador.

Uso: python prompts/graficos.py   (después de evaluar criterios y alertas)
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "img"
TAREAS = {"Tarea A: criterios": "criterios", "Tarea B: alertas": "alertas"}
SERIES = ("#2a78d6", "#eb6834")
BUENO, CRITICO, TINTA, TENUE, SUPERFICIE = "#0ca30c", "#d03b3b", "#1f1f1e", "#6b6a63", "#fcfcfb"


def cargar(carpeta):
    return json.loads((RAIZ / carpeta / "evaluar-promptfooconfig.json").read_text(encoding="utf-8"))


def ejes_limpios(ax):
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(TENUE)
    ax.tick_params(colors=TENUE, length=0)


def tasas_por_version():
    fig, ax = plt.subplots(figsize=(7.5, 3.6), facecolor=SUPERFICIE)
    ejes_limpios(ax)
    ancho = 0.36
    for i, (nombre, carpeta) in enumerate(TAREAS.items()):
        resumen = cargar(carpeta)["resumen"]
        versiones = list(resumen)
        x = [j + (i - 0.5) * (ancho + 0.02) for j in range(len(versiones))]
        tasas = [resumen[v]["tasa"] for v in versiones]
        barras = ax.bar(x, tasas, ancho, color=SERIES[i], label=nombre, zorder=2)
        for b, v in zip(barras, versiones):
            r = resumen[v]
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 2, f"{r['aprobados']}/{r['total']}",
                    ha="center", va="bottom", fontsize=9, color=TINTA)
        ax.set_xticks(range(len(versiones)), versiones)
    ax.axhline(85, color=TENUE, lw=1, ls="--", zorder=1)
    ax.text(-0.55, 87, "meta 85 %", fontsize=8, color=TENUE)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100], ["0 %", "25 %", "50 %", "75 %", "100 %"])
    ax.grid(axis="y", color="#e4e3dd", lw=0.8, zorder=0)
    ax.set_title("Tasa de aprobación por versión del prompt (9 casos por tarea)", fontsize=11, color=TINTA, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left", labelcolor=TINTA)
    fig.tight_layout()
    fig.savefig(SALIDA / "tasas-por-version.png", dpi=160)


def casos_por_version():
    fig, ejes = plt.subplots(1, 2, figsize=(10, 4.4), facecolor=SUPERFICIE)
    for ax, (nombre, carpeta) in zip(ejes, TAREAS.items()):
        filas = cargar(carpeta)["filas"]
        versiones = list(dict.fromkeys(f["version"] for f in filas))
        casos = list(dict.fromkeys(f["caso"] for f in filas))
        ax.set_facecolor(SUPERFICIE)
        for f in filas:
            x, y = versiones.index(f["version"]), casos.index(f["caso"])
            ax.add_patch(plt.Rectangle((x + 0.03, y + 0.06), 0.94, 0.88, color=BUENO if f["pasa"] else CRITICO,
                                       alpha=0.85 if f["pasa"] else 0.18, lw=0))
            fallos = [m.split("_")[0] for m, ok in f["metricas"].items() if not ok]
            texto = "✓ pasa" if f["pasa"] else "✗ " + " ".join(fallos)
            ax.text(x + 0.5, y + 0.5, texto, ha="center", va="center", fontsize=8,
                    color="white" if f["pasa"] else TINTA)
        ax.set_xlim(0, len(versiones))
        ax.set_ylim(len(casos), 0)
        ax.set_xticks([i + 0.5 for i in range(len(versiones))], versiones)
        ax.set_yticks([i + 0.5 for i in range(len(casos))], casos)
        ax.tick_params(colors=TENUE, length=0)
        for lado in ax.spines.values():
            lado.set_visible(False)
        ax.set_title(nombre, fontsize=10, color=TINTA, loc="left")
    fig.suptitle("Resultado de cada caso y aserciones que fallaron", fontsize=11, color=TINTA, x=0.02, ha="left")
    fig.tight_layout()
    fig.savefig(SALIDA / "casos-por-version.png", dpi=160)


if __name__ == "__main__":
    SALIDA.mkdir(exist_ok=True)
    tasas_por_version()
    casos_por_version()
