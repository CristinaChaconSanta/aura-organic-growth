"""Plataforma, plantilla y tipo de parámetro de cada URL.

Un error de plantilla se informa como «afecta a N páginas de producto», no URL por URL.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlsplit

_IDIOMA = re.compile(r"^[a-z]{2}(-[a-z]{2})?$")

_PARAMETROS = {
    "seguimiento": re.compile(r"^(utm_.*|gclid|fbclid|msclkid|ref|_ga|mc_.*|srsltid)$"),
    "orden": re.compile(r"^(sort|sort_by|orderby|order|orden|ordenar)$"),
    "pagina": re.compile(r"^(page|p|pagina|pag)$"),
    "variante": re.compile(r"^(variant|variante|sku)$"),
    "busqueda": re.compile(r"^(q|s|search|buscar|query|type)$"),
    "filtro": re.compile(r"^(filter.*|filtro.*|color|talla|size|price|precio|min_price|max_price|marca|brand|pa_.*|fq|map)$"),
}

_RUTAS = {
    "shopify": [
        (re.compile(r"^/collections/[^/]+/products/[^/]+"), "producto_en_coleccion"),
        (re.compile(r"^/products/[^/]+"), "producto"),
        (re.compile(r"^/collections/?$"), "listado_colecciones"),
        (re.compile(r"^/collections/[^/]+"), "coleccion"),
        (re.compile(r"^/pages/[^/]+"), "pagina"),
        (re.compile(r"^/blogs/[^/]+/tagged/"), "etiqueta"),
        (re.compile(r"^/blogs/[^/]+/[^/]+"), "articulo"),
        (re.compile(r"^/blogs/[^/]+/?$"), "blog"),
        (re.compile(r"^/search"), "busqueda"),
        (re.compile(r"^/(cart|account|checkout)"), "transaccional"),
    ],
    "wordpress": [
        (re.compile(r"^/(producto|product|tienda/[^/]+)/[^/]+"), "producto"),
        (re.compile(r"^/(categoria-producto|product-category)/"), "coleccion"),
        (re.compile(r"^/(etiqueta-producto|product-tag|tag|etiqueta)/"), "etiqueta"),
        (re.compile(r"^/(category|categoria)/"), "categoria_blog"),
        (re.compile(r"^/author/"), "autor"),
        (re.compile(r"^/(blog|noticias)/?$"), "blog"),
        (re.compile(r"^/\d{4}/\d{2}/"), "articulo"),
        (re.compile(r"^/(carrito|cart|checkout|finalizar-compra|mi-cuenta|my-account)"), "transaccional"),
    ],
    "vtex": [
        (re.compile(r"/p/?$"), "producto"),
        (re.compile(r"^/busca"), "busqueda"),
    ],
}


def plataforma(html: str, cabeceras: dict | None = None) -> str:
    texto = (html or "")[:400_000].casefold()
    claves = " ".join(f"{k}:{v}" for k, v in (cabeceras or {}).items()).casefold()
    if "cdn.shopify.com" in texto or "shopify" in claves or "/cdn/shop/" in texto:
        return "shopify"
    if "vtex" in texto or "vtex" in claves:
        return "vtex"
    if "wp-content" in texto or "wp-json" in texto:
        return "wordpress"
    if "wix.com" in texto or "wixstatic" in texto:
        return "wix"
    return "otra"


def _ruta_sin_idioma(ruta: str) -> str:
    partes = [p for p in ruta.split("/") if p]
    if partes and _IDIOMA.match(partes[0]) and len(partes) > 1:
        partes = partes[1:]
    return "/" + "/".join(partes)


def plantilla(url: str, plataforma_sitio: str = "otra") -> str:
    ruta = _ruta_sin_idioma(urlsplit(url).path or "/")
    if ruta == "/":
        return "portada"
    for patron, nombre in _RUTAS.get(plataforma_sitio, []):
        if patron.search(ruta):
            return nombre
    primero = ruta.strip("/").split("/")[0]
    return f"/{primero}/" if ruta.count("/") > 1 else "pagina"


def tipo_parametro(nombre: str) -> str:
    nombre = nombre.casefold()
    for tipo, patron in _PARAMETROS.items():
        if patron.match(nombre):
            return tipo
    return "otro"


def parametros(url: str) -> list[tuple[str, str]]:
    """[(nombre, tipo)] de la query de la URL."""
    return [(nombre, tipo_parametro(nombre)) for nombre, _ in parse_qsl(urlsplit(url).query, keep_blank_values=True)]


def es_paginacion(url: str) -> bool:
    tipos = {tipo for _, tipo in parametros(url)}
    return tipos == {"pagina"} or bool(re.search(r"/page/\d+/?$", urlsplit(url).path))
