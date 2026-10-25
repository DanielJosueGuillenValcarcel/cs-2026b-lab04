"""Genera img/metricas.png con los valores de radon-antes.txt y radon-despues.txt."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DATOS = [
    ("Complejidad del método principal\n(procesar)", [26, 5]),
    ("Complejidad promedio", [6.2, 1.74]),
    ("Líneas de código (SLOC)", [127, 356]),
]

fig, ejes = plt.subplots(1, 3, figsize=(11, 3.6))
for eje, (titulo, valores) in zip(ejes, DATOS):
    barras = eje.bar(["Antes", "Con patrones"], valores, color=["#9AA5B1", "#C0392B"], width=0.55)
    eje.set_title(titulo, fontsize=11)
    for barra, v in zip(barras, valores):
        eje.text(barra.get_x() + barra.get_width() / 2, barra.get_height(), f"{v:g}".replace(".", ","),
                 ha="center", va="bottom", fontsize=11, fontweight="bold")
    eje.spines[["top", "right"]].set_visible(False)
    eje.set_ylim(0, max(valores) * 1.18)
fig.suptitle("AireMisti IoT — radon 6.0.1 antes y después del refactor", fontsize=12)
fig.tight_layout()
fig.savefig("img/metricas.png", dpi=160)
