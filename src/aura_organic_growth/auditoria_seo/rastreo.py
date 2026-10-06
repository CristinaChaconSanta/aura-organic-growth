"""Rastreo de todas las URLs del sitemap más la paginación, y verificación de los
enlaces internos que no se rastrearon.

El archivo del rastreo puede pesar gigabytes: se lee línea por línea.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterator
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

from aura_organic_growth.auditoria_seo.robots import permitido

UA = "AuraOrganicGrowth/1.0 (auditoria)"
MAX_REDIRECCIONES = 10
MAX_BYTES_HTML = 600_000
TEMPORALES = {429, 503}
ESPERAS_LIMITE = (10, 30, 90)
PAGINACION = r"[?&](page|p|pagina|pag)=\d+$|/page/\d+/?$"

COLUMNAS = [
    r"^url$", r"^status$", r"^title$", r"^meta_desc$", r"^h[1-6]$", r"^canonical$",
    r"^meta_robots$", r"^meta_googlebot$", r"^redirect_", r"^links_", r"^body_text$",
    r"^size$", r"^depth$", r"^jsonld_", r"^img_", r"^alt_", r"^og:", r"^crawl_time$",
    r"^download_latency$", r"^errors$", r"^blocked_by_robotstxt$", r"^viewport$",
    r"(?i)^resp_headers_(x-robots-tag|content-type|last-modified)$",
]
SELECTORES = {
    "meta_robots": "//meta[translate(@name,'ROBTS','robts')='robots']/@content",
    "meta_googlebot": "//meta[translate(@name,'GOLEBT','golebt')='googlebot']/@content",
}


_ESCAPE = re.compile(r"%[0-9a-fA-F]{2}")


def normalizar(url: str) -> str:
    """%e2 y %E2 son la misma URL (RFC 3986): los escapes van en mayúscula."""
    partes = urlsplit(url.strip())
    mayus = lambda texto: _ESCAPE.sub(lambda m: m.group(0).upper(), texto)  # noqa: E731
    return urlunsplit((partes.scheme.lower(), partes.netloc.lower(), mayus(partes.path or "/"), mayus(partes.query), ""))


def fallida(fila: dict) -> bool:
    """Sin respuesta usable: el servidor limitó (429/503) o no respondió. Se reintenta, no es un error."""
    status = fila.get("status")
    if isinstance(status, (int, float)) and status == status:
        return int(status) in TEMPORALES
    return True


def host_base(host: str) -> str:
    return host.lower().removeprefix("www.")


RUTAS_DE_CUENTA = re.compile(
    r"^/(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:account|customer_authentication|cart|checkouts?|my-account|wp-admin|wp-login\.php|login)(?:/|$)",
    re.IGNORECASE,
)


def es_interna(url: str, host: str) -> bool:
    """Interna y de contenido: login, carrito y checkout responden distinto a un bot y no son SEO."""
    partes = urlsplit(url)
    return (
        partes.scheme in ("http", "https")
        and host_base(partes.netloc) == host_base(host)
        and not RUTAS_DE_CUENTA.match(partes.path)
    )


def rastrear(
    urls: list[str],
    destino: Path,
    *,
    host: str,
    retardo: float = 0.25,
    concurrencia: int = 4,
    max_paginas: int = 30_000,
    retomar: bool = False,
    tiempo_max: int = 0,
) -> Path:
    """tiempo_max en segundos (0 = sin tope); lo cortado se sigue con retomar=True."""
    import advertools as adv

    bin_entorno = str(Path(sys.executable).parent)
    if bin_entorno not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = bin_entorno + os.pathsep + os.environ.get("PATH", "")
    if destino.exists() and not retomar:
        destino.unlink()
    hechas = ya_rastreadas(destino) if destino.exists() else set()
    previas = fallidas_previas(destino) if destino.exists() else []
    faltan = [url for url in dict.fromkeys([*urls, *previas]) if normalizar(url) not in hechas]
    cupo = max_paginas - len(hechas)
    if cupo <= 0 or not faltan:
        return destino
    adv.crawl(
        faltan[:cupo],
        str(destino),
        follow_links=True,
        allowed_domains=[host, host_base(host)],
        include_url_regex=PAGINACION,
        xpath_selectors=SELECTORES,
        keep_columns=COLUMNAS,
        custom_settings={
            "USER_AGENT": UA,
            "ROBOTSTXT_OBEY": True,
            "DOWNLOAD_DELAY": retardo,
            "CONCURRENT_REQUESTS": concurrencia,
            "CONCURRENT_REQUESTS_PER_DOMAIN": concurrencia,
            "AUTOTHROTTLE_ENABLED": True,
            "AUTOTHROTTLE_TARGET_CONCURRENCY": max(1.0, concurrencia / 2),
            "CLOSESPIDER_PAGECOUNT": cupo,
            "CLOSESPIDER_TIMEOUT": tiempo_max,
            "RETRY_TIMES": 3,
            "DOWNLOAD_TIMEOUT": 90,
            "LOG_LEVEL": "WARNING",
        },
    )
    return destino


def ya_rastreadas(destino: Path) -> set[str]:
    """URLs pedidas y finales de un rastreo anterior, para retomarlo sin repetir. Las fallidas se vuelven a pedir."""
    hechas: set[str] = set()
    with destino.open(encoding="utf-8") as archivo:
        for linea in archivo:
            try:
                fila = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if fallida(fila):
                continue
            hechas.add(normalizar(str(fila.get("url") or "")))
            hechas.update(normalizar(u) for u in _lista(fila.get("redirect_urls")) if u)
    return hechas


def fallidas_previas(destino: Path) -> list[str]:
    """Las que fallaron en un rastreo anterior, también las de paginación que no están en el sitemap."""
    salida: list[str] = []
    with destino.open(encoding="utf-8") as archivo:
        for linea in archivo:
            try:
                fila = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if fallida(fila) and fila.get("url"):
                salida.append(normalizar(str(fila["url"])))
    return list(dict.fromkeys(salida))


def _lista(valor) -> list[str]:
    if valor is None or (isinstance(valor, float) and valor != valor):
        return []
    return [parte.strip() for parte in str(valor).split("@@")]


def _cabecera(fila: dict, nombre: str) -> str:
    clave = f"resp_headers_{nombre}".casefold()
    return next((str(v) for k, v in fila.items() if k.casefold() == clave and v), "")


def es_noindex(*directivas: str) -> bool:
    texto = " ".join(directivas).casefold()
    return bool(re.search(r"\b(noindex|none)\b", texto))


def huella(texto: str) -> str:
    plano = " ".join(str(texto or "").casefold().split())
    return hashlib.sha1(plano.encode("utf-8")).hexdigest()[:16] if plano else ""


def compactar(fila: dict, host: str) -> dict:
    url = normalizar(str(fila.get("url") or ""))
    pedidas = [normalizar(u) for u in _lista(fila.get("redirect_urls")) if u]
    codigos = [c for c in _lista(fila.get("redirect_reasons")) if c]
    destinos = _lista(fila.get("links_url"))
    nofollow = _lista(fila.get("links_nofollow"))
    enlaces = []
    for indice, destino in enumerate(destinos):
        if destino and es_interna(destino, host):
            seguir = not (indice < len(nofollow) and nofollow[indice].casefold() == "true")
            enlaces.append((sys.intern(normalizar(destino)), seguir))
    status = fila.get("status")
    robots = [str(fila.get("meta_robots") or ""), str(fila.get("meta_googlebot") or ""), _cabecera(fila, "x-robots-tag")]
    cuerpo = fila.get("body_text") or ""
    return {
        "url": url,
        "pedida": pedidas[0] if pedidas else url,
        "redirecciones": list(zip(pedidas, codigos)),
        "status": int(status) if isinstance(status, (int, float)) and status == status else None,
        "error": str(fila.get("errors") or ""),
        "tipo": _cabecera(fila, "content-type"),
        "title": [t for t in _lista(fila.get("title")) if t],
        "meta_desc": [t for t in _lista(fila.get("meta_desc")) if t],
        "h1": _lista(fila.get("h1")),
        "canonical": sorted({normalizar(urljoin(url, c)) for c in _lista(fila.get("canonical")) if c}),
        "robots": " | ".join(r for r in robots if r and r != "nan"),
        "noindex": es_noindex(*robots),
        "enlaces": enlaces,
        "huella": huella(cuerpo),
        "palabras": len(str(cuerpo).split()),
        "profundidad": fila.get("depth"),
    }


def paginas(destino: Path, host: str) -> Iterator[dict]:
    """Una vez por URL: advertools parte las listas largas y cada tramo puede repetir la paginación.

    Si un reintento respondió, la fila fallida anterior de esa URL se descarta.
    """
    logradas = ya_rastreadas(destino)
    vistas: set[str] = set()
    with destino.open(encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea:
                continue
            try:
                fila = json.loads(linea)
            except json.JSONDecodeError:
                continue
            pagina = compactar(fila, host)
            if fallida(fila) and pagina["url"] in logradas:
                continue
            if pagina["url"] not in vistas:
                vistas.add(pagina["url"])
                yield pagina


_LINK = re.compile(r"<link\b[^>]*>", re.I)
_META = re.compile(r"<meta\b[^>]*>", re.I)
_ATRIBUTO = r"""\b{}\s*=\s*["']([^"']*)["']"""


def _atributo(etiqueta: str, nombre: str) -> str:
    hallado = re.search(_ATRIBUTO.format(nombre), etiqueta, re.I)
    return hallado.group(1).strip() if hallado else ""


def leer_cabeza(html: str, url: str) -> tuple[list[str], str]:
    """(canonicals, directivas robots) del HTML crudo."""
    canonicals = sorted({
        normalizar(urljoin(url, _atributo(tag, "href")))
        for tag in _LINK.findall(html)
        if _atributo(tag, "rel").casefold() == "canonical" and _atributo(tag, "href")
    })
    robots = [
        _atributo(tag, "content")
        for tag in _META.findall(html)
        if _atributo(tag, "name").casefold() in ("robots", "googlebot")
    ]
    return canonicals, " | ".join(r for r in robots if r)


def _pausa(resp: requests.Response, intento: int) -> float:
    pedida = resp.headers.get("Retry-After", "")
    return float(pedida) if pedida.isdigit() else ESPERAS_LIMITE[intento]


def _pedir(http: requests.Session, url: str, espera: float, dormir=time.sleep) -> requests.Response:
    """Reintenta 429 y 503 con la espera que pide el servidor."""
    for intento in range(len(ESPERAS_LIMITE) + 1):
        resp = http.get(url, headers={"User-Agent": UA}, timeout=60, allow_redirects=False, stream=True)
        dormir(espera)
        if resp.status_code not in TEMPORALES or intento == len(ESPERAS_LIMITE):
            return resp
        resp.close()
        dormir(min(_pausa(resp, intento), 120))
    return resp


def _una(url: str, reglas: list, http: requests.Session, espera: float, dormir=time.sleep) -> dict:
    if not permitido(url, reglas):
        return {"estado": "bloqueada por robots"}
    cadena: list[tuple[str, int]] = []
    actual = url
    try:
        for _ in range(MAX_REDIRECCIONES + 1):
            resp = _pedir(http, actual, espera, dormir)
            if resp.status_code in TEMPORALES:
                resp.close()
                return {"estado": "limitada", "status": resp.status_code, "cadena": cadena}
            if resp.is_redirect and resp.headers.get("Location"):
                cadena.append((actual, resp.status_code))
                actual = normalizar(urljoin(actual, resp.headers["Location"]))
                resp.close()
                continue
            html = ""
            if resp.status_code == 200 and "html" in resp.headers.get("Content-Type", ""):
                html = resp.raw.read(MAX_BYTES_HTML, decode_content=True).decode(resp.encoding or "utf-8", "replace")
            resp.close()
            canonicals, robots = leer_cabeza(html, actual)
            robots = " | ".join(r for r in (robots, resp.headers.get("X-Robots-Tag", "")) if r)
            return {
                "estado": "ok",
                "status": resp.status_code,
                "final": actual,
                "cadena": cadena,
                "canonical": canonicals,
                "robots": robots,
                "noindex": es_noindex(robots),
            }
        return {"estado": "ok", "status": None, "final": actual, "cadena": cadena, "error": "demasiadas redirecciones"}
    except requests.RequestException as exc:
        return {"estado": "error", "error": type(exc).__name__, "cadena": cadena}


def verificar(
    urls: list[str],
    reglas: list,
    *,
    session: requests.Session | None = None,
    concurrencia: int = 2,
    espera: float = 1.0,
) -> dict[str, dict]:
    http = session or requests.Session()
    with ThreadPoolExecutor(max_workers=concurrencia) as pool:
        resultados = pool.map(lambda u: _una(u, reglas, http, espera), urls)
        return dict(zip(urls, resultados))
