"""Explicación de alertas con IA.

Adapter por proveedor, Decorator de caché y una Chain of Responsibility de
guardrails que revisa la respuesta antes de mostrarla al ciudadano.
"""
from __future__ import annotations

import re
from typing import Protocol


class ProveedorLLM(Protocol):
    def completar(self, prompt: str) -> str: ...


class OpenAIAdapter:
    def __init__(self, cliente, modelo: str = "gpt-4o-mini"):
        self.cliente = cliente
        self.modelo = modelo

    def completar(self, prompt):
        r = self.cliente.chat_completions_create(model=self.modelo,
                                                 messages=[{"role": "user", "content": prompt}])
        return r["choices"][0]["message"]["content"]


class GeminiAdapter:
    def __init__(self, cliente):
        self.cliente = cliente

    def completar(self, prompt):
        return self.cliente.generate_content(prompt).text


class ConCache:
    """Decorator: el mismo prompt no se paga dos veces."""

    def __init__(self, proveedor: ProveedorLLM):
        self.proveedor = proveedor
        self._cache: dict[str, str] = {}

    def completar(self, prompt):
        if prompt not in self._cache:
            self._cache[prompt] = self.proveedor.completar(prompt)
        return self._cache[prompt]


class FabricaProveedores:
    def __init__(self, adaptadores: dict[str, type] | None = None):
        self._registro = dict(adaptadores or {"OPENAI": OpenAIAdapter, "GEMINI": GeminiAdapter})

    def registrar(self, nombre: str, adaptador: type):
        self._registro[nombre] = adaptador

    def crear(self, nombre: str, cliente) -> ProveedorLLM:
        try:
            return ConCache(self._registro[nombre](cliente))
        except KeyError:
            raise ValueError(f"Proveedor de IA no soportado: {nombre}") from None


class GuardrailRechazo(ValueError):
    pass


class Guardrail:
    """Eslabón de la cadena: revisa y pasa al siguiente."""

    def __init__(self):
        self.siguiente: Guardrail | None = None

    def luego(self, otro: "Guardrail") -> "Guardrail":
        self.siguiente = otro
        return otro

    def revisar(self, texto: str, alerta) -> str:
        self.validar(texto, alerta)
        return self.siguiente.revisar(texto, alerta) if self.siguiente else texto

    def validar(self, texto, alerta):
        raise NotImplementedError


class NoInventaPM10(Guardrail):
    def validar(self, texto, alerta):
        for valor in re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:µg/m³|ug/m3)", texto):
            if abs(float(valor.replace(",", ".")) - alerta.pm10_max) > 0.05:
                raise GuardrailRechazo(f"Guardrail: la IA inventó un valor de PM10 ({valor})")


class SinConsejosMedicos(Guardrail):
    PALABRAS = ("diagnóstico", "medicamento", "tratamiento", "cura")

    def validar(self, texto, alerta):
        for palabra in self.PALABRAS:
            if palabra in texto.lower():
                raise GuardrailRechazo(f"Guardrail: consejo médico no permitido ('{palabra}')")


class LongitudMaxima(Guardrail):
    def __init__(self, maximo: int = 400):
        super().__init__()
        self.maximo = maximo

    def validar(self, texto, alerta):
        if len(texto) > self.maximo:
            raise GuardrailRechazo("Guardrail: la explicación es demasiado larga para Telegram")


def cadena_por_defecto() -> Guardrail:
    primero = NoInventaPM10()
    primero.luego(SinConsejosMedicos()).luego(LongitudMaxima())
    return primero


class ExplicadorAlertas:
    def __init__(self, proveedor: ProveedorLLM, guardrails: Guardrail | None = None):
        self.proveedor = proveedor
        self.guardrails = guardrails or cadena_por_defecto()

    def explicar(self, alerta) -> str:
        prompt = (f"Explica en lenguaje sencillo, en menos de 60 palabras, que en {alerta.distrito} "
                  f"el PM10 llegó a {alerta.pm10_max:.1f} µg/m³ y qué precauciones tomar.")
        return self.guardrails.revisar(self.proveedor.completar(prompt), alerta)
