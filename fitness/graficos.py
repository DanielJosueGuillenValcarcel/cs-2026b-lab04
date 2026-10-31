"""Genera los gráficos de las iteraciones de ADD y la matriz de riesgos del ATAM-lite.

Uso: python -m fitness.graficos   (lee fitness/datos/experimentos.json, que produce fitness.experimentos)
"""
import json
import pathlib
from dataclasses import replace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from fitness import alertas, fiabilidad  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ADD = RAIZ / "docs" / "architecture" / "add" / "img"
ATAM = RAIZ / "docs" / "architecture" / "img"
GRIS, ROJO, AZUL, VERDE = "#9AA5B1", "#C0392B", "#2E6DA4", "#2E8B57"
COLORES = [GRIS, "#B8860B", AZUL, VERDE]


def _estilo(eje):
    eje.spines[["top", "right"]].set_visible(False)
    eje.grid(axis="y", alpha=0.3)


def iteracion_1():
    corridas = 100
    rs = [alertas.monte_carlo(p, corridas=corridas) for p in alertas.POLITICAS]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.4))
    nombres = ["Actual\n(Lab 05)", "8 workers", "Vigencia\ncorregida", "Frescura +\ncola prioritaria"]
    x = range(len(rs))
    a.bar([i - 0.2 for i in x], [r["p95_s"] for r in rs], 0.4, color=COLORES, label="p95 promedio")
    a.bar([i + 0.2 for i in x], [r["p95_peor_corrida_s"] for r in rs], 0.4, color=COLORES, alpha=0.45,
          hatch="//", label="p95 de la peor corrida")
    for i, r in enumerate(rs):
        a.text(i - 0.2, r["p95_s"], f'{r["p95_s"]:.1f}'.replace(".", ","), ha="center", va="bottom", fontsize=9)
        a.text(i + 0.2, r["p95_peor_corrida_s"], f'{r["p95_peor_corrida_s"]:.0f}', ha="center", va="bottom", fontsize=9)
    a.axhline(60, color=ROJO, ls="--", lw=1.2)
    a.text(3.45, 62, "QA-02: 60 s", color=ROJO, ha="right", fontsize=9)
    a.set_xticks(list(x), nombres, fontsize=9)
    a.set_ylabel("Latencia de la alerta en vivo (s)")
    a.set_title(f"Reconexión de 400 sensores tras 2 h de corte ({corridas} corridas)", fontsize=10.5)
    a.legend(fontsize=8.5, loc="upper right", bbox_to_anchor=(1, 0.93))
    _estilo(a)

    xs = list(range(0, 30, 2))
    for pol, color in ((alertas.ACTUAL, GRIS), (alertas.VIGENCIA, AZUL), (alertas.ADOPTADA, VERDE)):
        ys = [alertas.monte_carlo(pol, alertas.Escenario(distritos_con_pico_en_corte=k), corridas=40)["p95_peor_corrida_s"]
              for k in xs]
        b.plot(xs, ys, marker="o", ms=3.5, color=color, label=pol.nombre)
    b.axhline(60, color=ROJO, ls="--", lw=1.2)
    b.set_xlabel("Distritos con picos de PM10 durante el corte")
    b.set_ylabel("p95 de la alerta en vivo, peor corrida (s)")
    b.set_title("Punto de sensibilidad: alertas antiguas frente al límite de Telegram", fontsize=10.5)
    b.legend(fontsize=8.5)
    _estilo(b)
    fig.tight_layout()
    fig.savefig(ADD / "iteracion-1.png", dpi=150)
    return rs


def sensibilidad_distritos_en_vivo():
    filas = []
    for k in (3, 10, 15, 20, 25, 29):
        r = alertas.monte_carlo(alertas.ADOPTADA, alertas.Escenario(distritos_con_pico_en_vivo=k), corridas=40)
        filas.append((k, r["p95_peor_corrida_s"]))
    return filas


def iteracion_2(exp):
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(14, 4.3))
    etiquetas = ["Ingesta caída\n10 min, valores\npor defecto", "Ingesta caída\n10 min, infra/\nmosquitto",
                 "Broker kill -9,\nautosave 60 s", "Broker kill -9\n+ acuse de\naplicación"]
    valores = [exp["caida_ingesta_10min"]["defecto"]["perdidas"], exp["caida_ingesta_10min"]["infra"]["perdidas"],
               exp["caida_broker"]["autosave_60s"]["perdidas"], exp["caida_broker"]["autosave_60s_con_acuse"]["perdidas"]]
    barras = a.bar(range(4), valores, color=[GRIS, VERDE, GRIS, VERDE])
    for br, v in zip(barras, valores):
        a.text(br.get_x() + br.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=9, fontweight="bold")
    a.set_xticks(range(4), etiquetas, fontsize=8)
    a.set_ylabel("Lecturas perdidas")
    a.set_title("Experimento real con Mosquitto 2.0.18", fontsize=10.5)
    _estilo(a)

    rs = [fiabilidad.monte_carlo(c, meses=1000) for c in fiabilidad.CONFIGS]
    v = [max(r["media"], 0.5) for r in rs]
    barras = b.bar(range(3), v, color=[GRIS, AZUL, VERDE])
    b.set_yscale("log")
    for br, r in zip(barras, rs):
        b.text(br.get_x() + br.get_width() / 2, max(r["media"], 0.5), f'{r["media"]:,.0f}'.replace(",", " "),
               ha="center", va="bottom", fontsize=9, fontweight="bold")
    b.set_xticks(range(3), ["Por defecto", "Cola 200 000\n+ autosave 60 s", "+ acuse de\naplicación"], fontsize=8.5)
    b.set_ylabel("Lecturas perdidas por mes (media, escala log)")
    b.set_title("Monte Carlo: 1000 meses de operación", fontsize=10.5)
    _estilo(b)

    rend = exp["rendimiento_msg_s"]
    xs = [0, 1]
    c.bar([x - 0.2 for x in xs], [rend["4000_autosave_60s"], rend["20000_autosave_60s"]], 0.4, color=AZUL,
          label="autosave cada 60 s")
    c.bar([x + 0.2 for x in xs], [rend["4000_por_cambio"], rend["20000_por_cambio"]], 0.4, color=ROJO,
          label="guardar en cada cambio")
    for x, k in zip(xs, ("4000", "20000")):
        c.text(x - 0.2, rend[f"{k}_autosave_60s"], f'{rend[f"{k}_autosave_60s"]:.0f}', ha="center", va="bottom", fontsize=9)
        c.text(x + 0.2, rend[f"{k}_por_cambio"], f'{rend[f"{k}_por_cambio"]:.0f}', ha="center", va="bottom", fontsize=9)
    c.set_xticks(xs, ["4 000 en cola", "20 000 en cola"], fontsize=9)
    c.set_ylabel("Mensajes por segundo aceptados")
    c.set_title("Trade-off: persistir cada mensaje", fontsize=10.5)
    c.set_ylim(0, 7000)
    c.legend(fontsize=8.5, loc="upper center", ncol=2)
    _estilo(c)
    fig.tight_layout()
    fig.savefig(ADD / "iteracion-2.png", dpi=150)
    return rs


RIESGOS = [
    ("R1", "Un solo VPS", 2, 5),
    ("R2", "Episodio en >20 distritos a la vez", 2, 4),
    ("R3", "Redis pierde tareas al reiniciarse", 2, 3),
    ("R4", "Clave de un sensor filtrada", 2, 3),
    ("R5", "microSD llena en cortes largos", 1, 3),
    ("R6", "Reloj del sensor atrasado", 3, 4),
]


def matriz_riesgos():
    fig, a = plt.subplots(figsize=(6.6, 5.2))
    for p in range(1, 6):
        for i in range(1, 6):
            puntaje = p * i
            color = "#F5B7B1" if puntaje >= 12 else "#FCF3CF" if puntaje >= 6 else "#D5F5E3"
            a.add_patch(plt.Rectangle((p - 0.5, i - 0.5), 1, 1, color=color, ec="white"))
    vistos = {}
    for rid, texto, p, i in RIESGOS:
        k = vistos.get((p, i), 0)
        vistos[(p, i)] = k + 1
        a.text(p, i + 0.22 - 0.3 * k, rid, ha="center", va="center", fontsize=10, fontweight="bold",
               bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#555"))
    a.set_xlim(0.5, 5.5)
    a.set_ylim(0.5, 5.5)
    a.set_xticks(range(1, 6))
    a.set_yticks(range(1, 6))
    a.set_xlabel("Probabilidad (1 a 5)")
    a.set_ylabel("Impacto (1 a 5)")
    a.set_title("Matriz de riesgos del ATAM-lite (antes de mitigar)", fontsize=11)
    leyenda = "\n".join(f"{r}: {t}" for r, t, _, _ in RIESGOS)
    a.text(5.65, 3, leyenda, fontsize=8.5, va="center")
    fig.tight_layout()
    fig.savefig(ATAM / "matriz-riesgos.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    ADD.mkdir(parents=True, exist_ok=True)
    ATAM.mkdir(parents=True, exist_ok=True)
    exp = json.loads((pathlib.Path(__file__).parent / "datos" / "experimentos.json").read_text())
    for r in iteracion_1():
        print(r)
    print("sensibilidad distritos en vivo:", sensibilidad_distritos_en_vivo())
    for r in iteracion_2(exp):
        print(r)
    matriz_riesgos()
