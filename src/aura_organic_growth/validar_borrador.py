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
    "jerga_tecnica",
    "mas_de_un_dato",
    "enlace",
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
# Nombrar a ChatGPT o Gemini es el gancho y se permite. Se rechaza prometer que
# una IA va a mencionar, citar o recomendar al negocio.
_MOTOR = r"(?:chat\s*gpt|gemini|perplexity|claude|\bia\b|inteligencia artificial)"
_IA = re.compile(
    r"(?:va|vas|van|vamos|vai|v[aã]o)\s+(?:a\s+)?(?:mencionar|citar|recomendar|nombrar|aparecer)|"
    r"\b(?:mencionar|citar|recomendar|aparecer)(?:[aá][sn]?|emos)\b|"
    r"\b(?:ir[aá]|ser[aá])\s+(?:mencionar|citad|recomendad)\w*|"
    r"apare(?:cer|zcas|zca|zcan)\s+en\s+(?:la\s+)?" + _MOTOR + r"|"
    r"(?:hacer|lograr|conseguir|ayud\w+\s+a)\s+(?:que\s+)?[^.!?\n]{0,60}?(?:aparec|mencion|cit|recomien)\w*|"
    r"(?:garantiz\w*|asegur\w*|promet\w*|garant\w+)[^.!?\n]{0,60}(?:aparec|mencion|cit|recomend|" + _MOTOR + r")",
    re.IGNORECASE,
)
_JERGA = re.compile(
    r"(?<![a-z0-9])(?:ms|milisegundos?|milissegundos?|lcp|html|wayback|dataforseo|pagespeed|page\s+speed|"
    r"serper|labs|intersecciones|origen(?:es)?|origem|crawlers?|schema|scrap(?:er|ers|ing)|algoritmos?|"
    r"geo|aeo|h[1-6]|alt|meta\s*descrip\w*|json-?ld|llms\.?txt|dashboard)(?![a-z0-9])"
)
# El primer email va en texto plano: el informe se ofrece y se manda solo si responden.
_ENLACE = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(?:com|cl|mx|co|br|io|net|org)/", re.IGNORECASE)
_FECHA = re.compile(
    r"\d{4}-\d{2}-\d{2}|\b\d{1,2}\s+de\s+[a-zA-Záéíóúñ]+(?:\s+de\s+\d{4})?|\b20\d{2}\b",
    re.IGNORECASE,
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


def _cuatro_palabras(texto: str) -> set[tuple[str, ...]]:
    palabras = re.findall(r"\w+", _plano(texto))
    return {tuple(palabras[i : i + 4]) for i in range(len(palabras) - 3)}


def _cita_medicion(borrador: str, hallazgos: list[dict]) -> bool:
    """Cita una cifra de la fila o repite, con cuatro palabras seguidas, lo que la fila midió."""
    if not hallazgos:
        return False
    if any(_cifra_esta(numero, unidad, hallazgos) for numero, unidad in _pares(borrador)):
        return True
    return bool(_cuatro_palabras(borrador) & _cuatro_palabras(_blob(hallazgos)))


def _jerga(borrador: str) -> bool:
    return bool(_JERGA.search(_plano(borrador)))


def _mas_de_un_dato(borrador: str) -> bool:
    """Más de una cifra distinta. El umbral de 2,5 s solo acompaña a los segundos medidos."""
    sin_fechas = _FECHA.sub(" ", borrador or "")
    numeros = {_normalizar_numero(h.group("num")) for h in _CIFRA.finditer(sin_fechas)}
    if "2.5" in numeros and len(numeros) > 1:
        numeros.discard("2.5")
    return len(numeros) > 1


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
    if _jerga(texto):
        razones.append("jerga_tecnica")
    if _mas_de_un_dato(texto):
        razones.append("mas_de_un_dato")
    if _ENLACE.search(texto.replace("aurathinking.com", "")):
        razones.append("enlace")
    blob = _blob(hallazgos)
    if not _cita_medicion(texto, hallazgos) or _nombres_fuera(texto, blob, _permitidos(empresa, contacto)):
        razones.append("afirmacion_fuera_de_hallazgos")
    return razones
