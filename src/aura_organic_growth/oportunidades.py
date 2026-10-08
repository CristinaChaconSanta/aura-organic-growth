"""Oportunidades medidas en el rastreo (advertools) o en la portada.

Title vacío, meta description vacía, H1 vacío y página de venta rota son
oportunidad observada. «No determinable» queda solo cuando la página no se
pudo medir: sin respuesta, 429 o 503. Un inventario a medias no borra lo ya medido.
"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlsplit

from aura_organic_growth.auditoria_seo.plantillas import plantilla

LIMITADAS = {429, 503}
EJEMPLOS = 5
_TITLE = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.IGNORECASE | re.DOTALL)
_H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1\s*>", re.IGNORECASE | re.DOTALL)
_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATRIBUTO = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_ETIQUETA = re.compile(r"<[^>]+>")
_VENTA = re.compile(
    r"/(servicios?|services?|productos?|products?|tienda|shop|cotizar|cotizacion|cotización)(/|$)",
    re.IGNORECASE,
)
_PLANTILLAS_VENTA = {"portada", "producto", "producto_en_coleccion", "coleccion"}

_FICHAS = {
    "pagina_venta_rota": {
        "titulo": "Páginas de venta que no abren",
        "uno": "1 página de venta respondió con error.",
        "varios": "{n} páginas de venta respondieron con error.",
        "consecuencia": "Quien quiere comprar llega a una página rota y se va.",
        "criterio": (
            "Portada, producto, colección o página de servicio que responde 4xx o 5xx. "
            "Un 429 o un 503 es límite del servidor: no es página rota y no es oportunidad."
        ),
    },
    "title_vacio": {
        "titulo": "Páginas sin título",
        "uno": "1 página respondió sin título.",
        "varios": "{n} páginas respondieron sin título.",
        "consecuencia": "En Google y en una respuesta de IA esa página no dice qué vende.",
        "criterio": "El título iba vacío en el HTML que respondió 200. No se afirma si la página no respondió.",
    },
    "meta_vacia": {
        "titulo": "Páginas sin descripción para buscadores",
        "uno": "1 página respondió sin descripción para buscadores.",
        "varios": "{n} páginas respondieron sin descripción para buscadores.",
        "consecuencia": "El resultado de búsqueda no explica la oferta y el clic se va a quien sí la explica.",
        "criterio": "La meta description iba vacía en el HTML que respondió 200. No se afirma si la página no respondió.",
    },
    "h1_vacio": {
        "titulo": "Páginas sin título principal",
        "uno": "1 página respondió sin título principal.",
        "varios": "{n} páginas respondieron sin título principal.",
        "consecuencia": "Quien abre la página no ve, en el primer título, qué se vende.",
        "criterio": "El H1 iba vacío en el HTML que respondió 200. No se afirma si la página no respondió.",
    },
}


def _plano(crudo: str) -> str:
    return re.sub(r"\s+", " ", unescape(_ETIQUETA.sub(" ", crudo or ""))).strip()


def _meta_description(html: str) -> str:
    for etiqueta in _META.findall(html or ""):
        atributos = {k.lower(): (a or b) for k, a, b in _ATRIBUTO.findall(etiqueta)}
        if atributos.get("name", "").lower() == "description":
            return _plano(atributos.get("content", ""))
    return ""


def _textos(valor) -> list[str]:
    if valor is None:
        return []
    piezas = [valor] if isinstance(valor, str) else list(valor)
    return [str(pieza).strip() for pieza in piezas if str(pieza).strip()]


def es_pagina_de_venta(url: str, plataforma_sitio: str = "otra") -> bool:
    if plantilla(url, plataforma_sitio) in _PLANTILLAS_VENTA:
        return True
    return bool(_VENTA.search(urlsplit(url).path or "/"))


def desde_respuesta(url: str, status: int | None, html: str | None) -> dict:
    """Una portada ya pedida, en la forma que lee el rastreo."""
    if status != 200:
        return {"url": url, "status": status, "tipo": "text/html", "title": [], "meta_desc": [], "h1": []}
    titulo = _TITLE.search(html or "")
    h1 = _H1.search(html or "")
    title = _plano(titulo.group(1)) if titulo else ""
    principal = _plano(h1.group(1)) if h1 else ""
    meta = _meta_description(html or "")
    return {
        "url": url,
        "status": 200,
        "tipo": "text/html",
        "title": [title] if title else [],
        "meta_desc": [meta] if meta else [],
        "h1": [principal] if principal else [],
    }


def _hallazgo(clave: str, filas: list[dict]) -> dict | None:
    if not filas:
        return None
    ficha = _FICHAS[clave]
    n = len(filas)
    texto = ficha["uno"] if n == 1 else ficha["varios"].format(n=n)
    return {
        "id": clave,
        "tipo": "oportunidad",
        "titulo": ficha["titulo"],
        "texto": texto,
        "nivel": "observado",
        "alcance": "sitio",
        "afectadas": n,
        "ejemplos": filas[:EJEMPLOS],
        "criterio": ficha["criterio"],
        "origen_criterio": "criterio interno de Aura",
        "fuente": None,
        "consecuencia": ficha["consecuencia"],
    }


def de_paginas(paginas: list[dict], *, plataforma_sitio: str = "otra") -> list[dict]:
    """Agrupa lo medido. Una página limitada o sin respuesta no entra como oportunidad ni como rota."""
    rotas: list[dict] = []
    sin_titulo: list[dict] = []
    sin_meta: list[dict] = []
    sin_h1: list[dict] = []
    for pagina in paginas:
        status = pagina.get("status")
        if status in LIMITADAS or status is None:
            continue
        url = str(pagina.get("url") or "")
        if isinstance(status, int) and status >= 400:
            if es_pagina_de_venta(url, plataforma_sitio):
                rotas.append({"url": url, "status": status})
            continue
        if status != 200:
            continue
        tipo = str(pagina.get("tipo") or "")
        if tipo and "html" not in tipo.casefold():
            continue
        if not _textos(pagina.get("title")):
            sin_titulo.append({"url": url})
        if not _textos(pagina.get("meta_desc")):
            sin_meta.append({"url": url})
        if not _textos(pagina.get("h1")):
            sin_h1.append({"url": url})
    return [
        h for h in (
            _hallazgo("pagina_venta_rota", rotas),
            _hallazgo("title_vacio", sin_titulo),
            _hallazgo("meta_vacia", sin_meta),
            _hallazgo("h1_vacio", sin_h1),
        ) if h
    ]
