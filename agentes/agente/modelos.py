"""El 'cerebro' del agente es intercambiable (patrón Strategy del Lab 07).

Protocolo: el modelo recibe el historial y devuelve un JSON con
  {"pensamiento": "...", "accion": "<herramienta>", "args": {...}}   o
  {"pensamiento": "...", "final": "<respuesta para el usuario>"}
"""
import json, os


class ModeloGrabado:
    """Reproduce decisiones grabadas de un asistente de IA (trayectoria JSON).
    Las herramientas se ejecutan de verdad; solo las decisiones vienen de la grabación."""
    def __init__(self, archivo):
        self._decisiones = json.load(open(archivo, encoding="utf-8"))
        self._i = 0

    def decidir(self, historial: list) -> dict:
        d = self._decisiones[self._i]
        self._i += 1
        return d


class ModeloAnthropic:
    """Proveedor real (opcional). Requiere ANTHROPIC_API_KEY y el paquete anthropic."""
    def __init__(self, modelo="claude-sonnet-4-5", sistema=""):
        import anthropic
        self._cliente, self._modelo, self._sistema = anthropic.Anthropic(), modelo, sistema

    def decidir(self, historial: list) -> dict:
        r = self._cliente.messages.create(model=self._modelo, max_tokens=1024, system=self._sistema,
                                          messages=historial, temperature=0)
        return json.loads(r.content[0].text)


class ModeloInteractivo:
    """Sin clave de API: el estudiante copia el contexto a su asistente de IA (Claude.ai, ChatGPT,
    Gemini, Copilot Chat), pega aquí la respuesta JSON y la decisión se graba para reproducirla."""
    def __init__(self, grabar_en):
        self._archivo, self._decisiones = grabar_en, []

    def decidir(self, historial: list) -> dict:
        print("\n===== COPIE ESTO EN SU ASISTENTE DE IA =====")
        print(historial[0]["content"] if len(historial) == 1 else historial[-1]["content"])
        print("===== PEGUE LA RESPUESTA JSON (una línea) =====")
        d = json.loads(input("> "))
        self._decisiones.append(d)
        json.dump(self._decisiones, open(self._archivo, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return d
