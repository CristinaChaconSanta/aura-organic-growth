"""Rechaza un borrador que afirma algo que la fila no midió.

No redacta. No envía. No aprueba: eso lo hace Cristina.
"""

from __future__ import annotations

import re
import unicodedata

RAZONES = (
    "cifra_sin_fuente",
    "promesa_ranking",
    "promesa_aparicion_ia",
    "automatizacion",
    "afirmacion_fuera_de_hallazgos",
)

_PERMITIDOS = frozenset({"cristina", "aura", "studio"})
_CIFRA = re.compile(
    r"(?P<num>\d{1,3}(?:\.\d{3})+|\d{1,3}(?:,\d{3})+|\d+(?:[.,]\d+)?)"
    r"(?:\s*(?P<unit>%|ms|s|segundos?|horas?|minutos?|html)\b)?",
    re.IGNORECASE,
)
_RANKING = re.compile(
    r"primer(?:o|a)?\s+lugar|primeira\s+posi[cç][aã]o|#\s*1\b|"
    r"\branking\b|n[uú]mero\s+1\b|p[aá]gina\s+1\b|first\s+place|"
    r"posicionarte|posicionarlos|posicionamos|vamos a posicionar|"
    r"garantiz\w*\s+(?:el\s+)?(?:primer|ranking|posici)",
    re.IGNORECASE,
)
_IA = re.compile(
    r"chatgpt|chat\s*gpt|gemini|perplexity|"
    r"apare(?:cer|zcas|ce)\s+en\s+(?:la\s+)?(?:ia\b|inteligencia artificial)|"
    r"(?:la\s+ia|inteligencia artificial|chatgpt|gemini|perplexity).{0,40}(?:mencion|cit)|"
    r"(?:mencion|cit).{0,40}(?:la\s+ia|inteligencia artificial|chatgpt|gemini|perplexity)",
    re.IGNORECASE | re.DOTALL,
)
_AUTO = re.compile(
    r"automatiz|automaç|automacao|automate|automation|aura\s+flow|aura\s+transform",
    re.IGNORECASE,
)
_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9.&-]*")

_UNIDAD = {
    "s": "s",
    "seg": "s",
    "segundo": "s",
    "segundos": "s",
    "ms": "ms",
    "milisegundo": "ms",
    "milisegundos": "ms",
    "h": "h",
    "hora": "h",
    "horas": "h",
    "min": "min",
    "minuto": "min",
    "minutos": "min",
    "%": "%",
    "html": "html",
}


def _plano(texto: str) -> str:
    base = unicodedata.normalize("NFKD", (texto or "").casefold())
    return "".join(ch for ch in base if not unicodedata.combining(ch))


def _normalizar_numero(texto: str) -> str:
    limpio = texto.strip().replace(" ", "")
    if re.fullmatch(r"\d+,\d{1,2}", limpio):
        return limpio.replace(",", ".")
    if re.fullmatch(r"\d+\.\d{1,2}", limpio):
        return limpio
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", limpio):
        return limpio.replace(".", "")
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", limpio):
        return limpio.replace(",", "")
    return limpio.replace(",", ".")


def _unidad(texto: str | None) -> str:
    if not texto:
        return ""
    return _UNIDAD.get(texto.casefold(), texto.casefold())


def _pares(texto: str) -> set[tuple[str, str]]:
    pares = set()
    for hallado in _CIFRA.finditer(texto or ""):
        pares.add((_normalizar_numero(hallado.group("num")), _unidad(hallado.group("unit"))))
    return pares


def _blob(hallazgos: list[dict]) -> str:
    partes = []
    for hallazgo in hallazgos:
        for clave in ("texto", "evidencia", "fuente", "fecha", "consecuencia"):
            partes.append(str(hallazgo.get(clave) or ""))
    return "\n".join(partes)


def _disponibles(hallazgos: list[dict]) -> list[tuple[set[tuple[str, str]], str]]:
    return [(_pares(_blob([hallazgo])), _blob([hallazgo])) for hallazgo in hallazgos]


def _cifra_esta(numero: str, unidad: str, hallazgos: list[dict]) -> bool:
    return any(
        _cifra_en_hallazgo(numero, unidad, pares, texto)
        for pares, texto in _disponibles(hallazgos)
    )


def _cifra_sin_fuente(borrador: str, hallazgos: list[dict]) -> bool:
    for numero, unidad in _pares(borrador):
        if not _cifra_esta(numero, unidad, hallazgos):
            return True
    return False


def _cita_medicion(borrador: str, hallazgos: list[dict]) -> bool:
    if not hallazgos:
        return False
    return any(_cifra_esta(numero, unidad, hallazgos) for numero, unidad in _pares(borrador))


def _cifra_en_hallazgo(numero: str, unidad: str, pares: set[tuple[str, str]], texto: str) -> bool:
    if (numero, unidad) in pares:
        return True
    if unidad and (numero, "") in pares and _unidad_en_texto(unidad, texto):
        return True
    if not unidad and any(num == numero for num, _unit in pares):
        return True
    return False


def _unidad_en_texto(unidad: str, texto: str) -> bool:
    palabras = {_unidad(m.group("unit")) for m in _CIFRA.finditer(texto) if m.group("unit")}
    return unidad in palabras


def _nombres_fuera(borrador: str, blob: str, permitidos: set[str]) -> bool:
    plano_blob = _plano(blob)
    for oracion in re.split(r"[.!?\n]+", borrador):
        palabras = _PALABRA.findall(oracion)
        for palabra in palabras[1:]:
            if not palabra[:1].isupper():
                continue
            clave = _plano(palabra)
            if clave in permitidos or clave in plano_blob:
                continue
            return True
    return False


def _permitidos(empresa: str, contacto: str) -> set[str]:
    tokens = set(_PERMITIDOS)
    for texto in (empresa, contacto):
        for palabra in _PALABRA.findall(texto or ""):
            tokens.add(_plano(palabra))
    return tokens


def validar(
    borrador: str,
    hallazgos: list[dict],
    *,
    empresa: str = "",
    contacto: str = "",
) -> list[str]:
    """Lista de razones. Vacía si el borrador puede quedar en redactado."""
    texto = (borrador or "").strip()
    if not texto:
        return []
    razones = []
    if _cifra_sin_fuente(texto, hallazgos):
        razones.append("cifra_sin_fuente")
    if _RANKING.search(texto):
        razones.append("promesa_ranking")
    if _IA.search(texto):
        razones.append("promesa_aparicion_ia")
    if _AUTO.search(texto):
        razones.append("automatizacion")
    blob = _blob(hallazgos)
    if not _cita_medicion(texto, hallazgos) or _nombres_fuera(texto, blob, _permitidos(empresa, contacto)):
        razones.append("afirmacion_fuera_de_hallazgos")
    return razones
