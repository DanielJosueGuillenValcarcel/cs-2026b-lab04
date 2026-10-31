"""Ejecuta los experimentos reales con Mosquitto y guarda los resultados en datos/experimentos.json."""
import json
import pathlib

from fitness import broker

if __name__ == "__main__":
    base = [l for l in broker.ajustes_produccion() if not l.startswith("autosave")]
    por_cambio = base + ["autosave_on_changes true", "autosave_interval 1"]
    r = {
        "mosquitto": "2.0.18",
        "caida_ingesta_10min": {"defecto": broker.experimento_caida_ingesta(broker.DEFECTO),
                                "infra": broker.experimento_caida_ingesta(broker.ajustes_produccion())},
        "caida_broker": {"autosave_60s": broker.experimento_caida_broker(broker.ajustes_produccion()),
                         "autosave_por_cambio": broker.experimento_caida_broker(por_cambio),
                         "autosave_60s_con_acuse": broker.experimento_acuse(broker.ajustes_produccion())},
        "rendimiento_msg_s": {f"{n}_{k}": broker.experimento_rendimiento(v, mensajes=n)["mensajes_por_s"]
                              for n in (4000, 20000)
                              for k, v in (("autosave_60s", broker.ajustes_produccion()), ("por_cambio", por_cambio))},
        "acl": broker.experimento_acl(),
        "alta_50_sensores": broker.experimento_alta_sensores(),
    }
    salida = pathlib.Path(__file__).parent / "datos" / "experimentos.json"
    salida.write_text(json.dumps(r, indent=2, ensure_ascii=False))
    print(json.dumps(r, indent=2, ensure_ascii=False))
