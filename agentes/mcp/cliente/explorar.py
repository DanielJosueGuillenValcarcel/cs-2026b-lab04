"""Explora el servidor MCP como lo haría un host: descubre el catálogo y prueba cada primitiva.

Uso (desde la raíz del repositorio):
  python agentes/mcp/cliente/explorar.py                       cliente actual (protocolo 2026-07-28)
  python agentes/mcp/cliente/explorar.py --legacy              fuerza el saludo initialize (clientes 2025)
  python agentes/mcp/cliente/explorar.py --espia ARCHIVO.jsonl guarda el tráfico JSON-RPC con el espía
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

SERVIDOR = Path(__file__).resolve().parents[1] / "servidor_mcp" / "airemisti_mcp.py"


ESPIA = Path(__file__).resolve().parent / "espia.py"


def parametros(servidor: Path = SERVIDOR, espia: str | None = None) -> StdioServerParameters:
    if espia:
        return StdioServerParameters(command=sys.executable,
                                     args=[str(ESPIA), espia, "--", sys.executable, str(servidor)])
    return StdioServerParameters(command=sys.executable, args=[str(servidor)])


def etiqueta(t) -> str:
    return "solo lectura" if t.annotations and t.annotations.read_only_hint else "ESCRITURA"


async def explorar(legacy=False, espia=None):
    async with Client(parametros(espia=espia), mode="legacy" if legacy else "auto") as c:
        print(f"Servidor: {c.server_info.name} {c.server_info.version} | protocolo {c.protocol_version}\n")
        print("HERRAMIENTAS (las elige el modelo):")
        for t in (await c.list_tools()).tools:
            args = ", ".join(t.input_schema.get("properties", {}))
            print(f"  - {t.name}({args}) [{etiqueta(t)}]")
        print("\nRECURSOS (los elige la aplicación):")
        for r in (await c.list_resources()).resources:
            print(f"  - {r.uri}  {r.title}")
        for r in (await c.list_resource_templates()).resource_templates:
            print(f"  - {r.uri_template}  {r.title} (plantilla)")
        print("\nPROMPTS (los elige el usuario):")
        for p in (await c.list_prompts()).prompts:
            print(f"  - {p.name}({', '.join(a.name for a in p.arguments or [])})")

        print("\nPRUEBAS DE USO:")
        r = await c.call_tool("resumen_diario", {"dia": "2026-11-21", "distrito": "cerro"})
        print("  resumen_diario →", json.dumps(r.structured_content, ensure_ascii=False)[:150], "…")
        r = await c.call_tool("alertas_activas", {"momento": "2026-11-21T15:30"})
        print("  alertas_activas →", json.dumps(r.structured_content, ensure_ascii=False))
        r = await c.call_tool("lecturas_sensor", {"codigo": "AQP-99", "dia": "2026-11-21"})
        print("  lecturas_sensor(AQP-99) → is_error =", r.is_error, "|", r.content[0].text[:110])
        r = await c.read_resource("airemisti://adr/001")
        print("  read_resource(adr/001) →", r.contents[0].text.splitlines()[0])
        r = await c.get_prompt("boletin_diario", {"dia": "2026-11-21"})
        print("  get_prompt(boletin_diario) →", r.messages[0].content.text[:80], "…")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy", action="store_true")
    ap.add_argument("--espia")
    a = ap.parse_args()
    asyncio.run(explorar(a.legacy, a.espia))
