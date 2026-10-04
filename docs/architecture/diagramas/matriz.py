import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

criterios = ["Fiabilidad\ningesta (25%)", "Tiempo de\nentrega (20%)", "Costo\noperativo (15%)",
             "Simplicidad\noperativa (15%)", "Latencia\nalertas (10%)", "Modificabilidad\n(15%)"]
pesos = np.array([0.25, 0.20, 0.15, 0.15, 0.10, 0.15])
alternativas = {
    "Capas + HTTP": [3, 5, 5, 5, 4, 2],
    "Monolito modular + MQTT": [5, 4, 5, 4, 5, 4],
    "Microservicios + Kafka": [5, 1, 1, 1, 5, 5],
}
colores = ["#9E9E9E", "#2E7D32", "#2B4C8C"]
totales = {k: float(np.dot(pesos, v)) for k, v in alternativas.items()}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [2.2, 1]})
x = np.arange(len(criterios))
w = 0.26
for i, (nombre, puntajes) in enumerate(alternativas.items()):
    ax1.bar(x + (i - 1) * w, puntajes, w, label=nombre, color=colores[i])
ax1.set_xticks(x)
ax1.set_xticklabels(criterios, fontsize=9)
ax1.set_ylim(0, 5.8)
ax1.set_ylabel("Puntaje (1-5)")
ax1.set_title("Puntaje por criterio")
ax1.legend(loc="upper center", ncol=3, frameon=False, fontsize=9)
ax1.spines[["top", "right"]].set_visible(False)

nombres = list(totales.keys())
valores = [totales[n] for n in nombres]
barras = ax2.barh(nombres, valores, color=colores)
ax2.invert_yaxis()
ax2.set_xlim(0, 5)
ax2.set_title("Puntaje ponderado total")
for b, v in zip(barras, valores):
    ax2.text(v + 0.05, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontweight="bold")
ax2.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
plt.savefig("img/matriz-decision.png", dpi=180)
print(totales)
