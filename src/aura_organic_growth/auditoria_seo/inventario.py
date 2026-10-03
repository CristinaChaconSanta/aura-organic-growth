"""Todas las URLs de todos los sitemaps, con el sitemap de origen. Se cuentan todas."""

from __future__ import annotations

import gzip
from xml.etree import ElementTree as ET

import requests

UA = {"User-Agent": "AuraOrganicGrowth/1.0 (auditoria)"}
MAX_NIVELES = 4


def _nombre(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def leer_sitemap(contenido: bytes) -> tuple[list[str], list[dict]]:
    """(sitemaps hijos, URLs con lastmod). Acepta gzip."""
    if contenido[:2] == b"\x1f\x8b":
        contenido = gzip.decompress(contenido)
    raiz = ET.fromstring(contenido)
    hijos: list[str] = []
    urls: list[dict] = []
    for nodo in raiz:
        datos = {_nombre(hijo.tag): (hijo.text or "").strip() for hijo in nodo}
        loc = datos.get("loc")
        if not loc:
            continue
        if _nombre(nodo.tag) == "sitemap":
            hijos.append(loc)
        elif _nombre(nodo.tag) == "url":
            urls.append({"url": loc, "lastmod": datos.get("lastmod", "")})
    return hijos, urls


def inventario(sitemaps: list[str], session: requests.Session | None = None) -> dict:
    http = session or requests.Session()
    pendientes = [(mapa, 0) for mapa in sitemaps]
    vistos: set[str] = set()
    estado: dict[str, int | str] = {}
    urls: list[dict] = []
    ya: set[str] = set()
    while pendientes:
        mapa, nivel = pendientes.pop(0)
        if mapa in vistos or nivel > MAX_NIVELES:
            continue
        vistos.add(mapa)
        try:
            resp = http.get(mapa, headers=UA, timeout=60)
            if resp.status_code != 200:
                estado[mapa] = f"HTTP {resp.status_code}"
                continue
            hijos, filas = leer_sitemap(resp.content)
        except (requests.RequestException, ET.ParseError, OSError) as exc:
            estado[mapa] = type(exc).__name__
            continue
        pendientes.extend((hijo, nivel + 1) for hijo in hijos)
        estado[mapa] = len(filas)
        for fila in filas:
            if fila["url"] not in ya:
                ya.add(fila["url"])
                urls.append({**fila, "sitemap": mapa})
    return {"sitemaps": estado, "urls": urls}
