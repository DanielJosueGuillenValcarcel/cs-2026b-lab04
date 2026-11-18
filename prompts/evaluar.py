"""Evaluador local con las mismas aserciones que promptfoo, sobre las respuestas grabadas.

Uso:
  python prompts/evaluar.py prompts/criterios/promptfooconfig.yaml
  python prompts/evaluar.py prompts/criterios/promptfooconfig.yaml --compuerta v3.1 --minimo 85
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
from proveedor_grabado import leer_grabacion  # noqa: E402


def _ruta(base, valor):
    return base / valor.removeprefix("file://")


def _funcion(base, valor):
    archivo, nombre = valor.removeprefix("file://").split(":")
    spec = importlib.util.spec_from_file_location(f"asserts_{base.name}", base / archivo)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return getattr(modulo, nombre)


def aplicar(base, asercion, salida, variables):
    tipo, valor = asercion["type"], asercion.get("value")
    if tipo == "is-json":
        try:
            datos = json.loads(salida)
        except ValueError:
            return False
        if valor is None:
            return True
        esquema = json.loads(_ruta(base, valor).read_text(encoding="utf-8"))
        return not list(Draft7Validator(esquema).iter_errors(datos))
    if tipo == "not-icontains":
        return valor.lower() not in salida.lower()
    if tipo == "icontains":
        return valor.lower() in salida.lower()
    if tipo == "python":
        r = _funcion(base, valor)(salida, {"vars": variables})
        return r["pass"] if isinstance(r, dict) else bool(r)
    raise ValueError(f"Aserción no soportada por el evaluador local: {tipo}")


def cargar(config_path):
    base = config_path.parent
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    tests = config["tests"]
    if isinstance(tests, str):
        tests = yaml.safe_load(_ruta(base, tests).read_text(encoding="utf-8"))
    return base, config, tests


def evaluar(config_path):
    base, config, tests = cargar(config_path)
    por_defecto = (config.get("defaultTest") or {}).get("assert", [])
    filas = []
    varios = len(config["providers"]) > 1
    for prov, p in [(prov, p) for prov in config["providers"] for p in config["prompts"]]:
        proveedor = prov["config"]
        etiqueta = f"{prov['label']} {p['label']}" if varios else p["label"]
        plantilla = _ruta(base, p["id"]).read_text(encoding="utf-8")
        for t in tests:
            v = t["vars"]
            prompt = plantilla
            for k, val in v.items():
                prompt = prompt.replace("{{" + k + "}}", str(val)).replace("{{ " + k + " }}", str(val))
            try:
                salida = leer_grabacion(proveedor, prompt, v, p["label"])
            except FileNotFoundError:
                filas.append({"version": etiqueta, "caso": v["id"], "pasa": False, "metricas": {"sin_grabacion": False}})
                continue
            metricas = {a.get("metric", a["type"]): aplicar(base, a, salida, v)
                        for a in por_defecto + t.get("assert", [])}
            filas.append({"version": etiqueta, "caso": v["id"], "pasa": all(metricas.values()),
                          "metricas": metricas})
    return filas


def resumen(filas):
    versiones = {}
    for f in filas:
        versiones.setdefault(f["version"], []).append(f)
    return {v: {"aprobados": sum(f["pasa"] for f in fs), "total": len(fs),
                "tasa": round(100 * sum(f["pasa"] for f in fs) / len(fs), 1),
                "fallos": {f["caso"]: [m for m, ok in f["metricas"].items() if not ok]
                           for f in fs if not f["pasa"]}}
            for v, fs in versiones.items()}


def compuerta(filas, version, minimo):
    tabla = resumen(filas)
    orden = list(tabla)
    errores = []
    if tabla[version]["tasa"] < minimo:
        errores.append(f"{version}: {tabla[version]['tasa']} % < {minimo} %")
    i = orden.index(version)
    if i > 0:
        previa = {f["caso"]: f["pasa"] for f in filas if f["version"] == orden[i - 1]}
        actual = {f["caso"]: f["pasa"] for f in filas if f["version"] == version}
        errores += [f"Regresión en {c}: pasaba en {orden[i - 1]}" for c in actual
                    if previa.get(c) and not actual[c]]
    return errores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--compuerta")
    parser.add_argument("--minimo", type=float, default=85)
    args = parser.parse_args()
    filas = evaluar(args.config)
    tabla = resumen(filas)
    salida = args.config.parent / f"evaluar-{args.config.stem}.json"
    salida.write_text(json.dumps({"resumen": tabla, "filas": filas}, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    for v, r in tabla.items():
        print(f"{v:>6}: {r['aprobados']}/{r['total']} ({r['tasa']} %)  fallos: {r['fallos'] or '-'}")
    if args.compuerta:
        errores = compuerta(filas, args.compuerta, args.minimo)
        for e in errores:
            print("::error::" + e)
        sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
