"""Señales de compra de los últimos 6 meses. Solo lo verificable.

Wayback: dos digestos distintos de la portada son un cambio observado en
el archivo, no un rediseño afirmado. crt.sh: un certificado nuevo de un
subdominio. RSS: la fecha de la última publicación del blog, tal como la
declara el feed. La pauta activa no se busca: la anota Cristina.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

CDX = "https://web.archive.org/cdx/search/cdx"
CRT = "https://crt.sh/"
UA = {"User-Agent": "AuraOrganicGrowth/1.0 (diagnostico)"}
# WordPress publica /feed/; Webflow, /blog/rss.xml. Solo se prueban si la portada no declara un feed.
RUTAS_FEED = ("/feed/", "/blog/rss.xml")
TIPOS_FEED = ("application/rss+xml", "application/atom+xml")
_LINK = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_ATRIBUTO = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_PUBDATE = re.compile(r"<pubDate>\s*([^<]+?)\s*</pubDate>", re.IGNORECASE)
_ISO = re.compile(r"<(?:updated|published)>\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


def _hace_seis_meses(hoy: date) -> date:
    mes = hoy.month - 6
    anio = hoy.year
    if mes <= 0:
        mes += 12
        anio -= 1
    dia = min(hoy.day, 28)
    return date(anio, mes, dia)


def wayback(dominio: str, session=None, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    desde = _hace_seis_meses(hoy)
    if not dominio:
        return {"senal": "cambio de portada", "nivel": "no determinable", "detalle": "sin dominio"}
    http = session or __import__("requests")
    resp = http.get(
        CDX,
        params={
            "url": f"{dominio}/",
            "output": "json",
            "fl": "timestamp,digest,statuscode",
            "from": desde.strftime("%Y%m%d"),
            "to": hoy.strftime("%Y%m%d"),
            "filter": "statuscode:200",
            "limit": "40",
        },
        timeout=40,
    )
    if resp.status_code != 200:
        return {"senal": "cambio de portada", "nivel": "no determinable", "detalle": f"http_{resp.status_code}"}
    filas = resp.json() or []
    digestos = {fila[1] for fila in filas[1:] if len(fila) > 1 and fila[1]}
    if len(digestos) >= 2:
        return {
            "senal": "cambio de portada",
            "nivel": "inferido",
            "detalle": f"Wayback guarda {len(digestos)} HTML distintos de la portada desde {desde.isoformat()}",
        }
    if len(digestos) == 1:
        return {
            "senal": "cambio de portada",
            "nivel": "observado",
            "detalle": f"Wayback guarda un solo HTML de la portada desde {desde.isoformat()}",
        }
    return {"senal": "cambio de portada", "nivel": "no determinable", "detalle": "Wayback no devolvió capturas"}


def subdominios_nuevos(dominio: str, session=None, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    desde = _hace_seis_meses(hoy)
    if not dominio:
        return {"senal": "subdominio nuevo", "nivel": "no determinable", "nombres": []}
    http = session or __import__("requests")
    resp = http.get(CRT, params={"q": f"%.{dominio}", "output": "json"}, timeout=40)
    if resp.status_code != 200:
        return {"senal": "subdominio nuevo", "nivel": "no determinable", "detalle": f"http_{resp.status_code}", "nombres": []}
    nuevos = set()
    for entrada in resp.json() or []:
        bruto = str(entrada.get("not_before") or "")[:10]
        try:
            emitido = datetime.strptime(bruto, "%Y-%m-%d").date()
        except ValueError:
            continue
        if emitido < desde:
            continue
        for nombre in str(entrada.get("name_value") or "").splitlines():
            limpio = nombre.strip().lstrip("*.").casefold()
            if limpio in {dominio.casefold(), f"www.{dominio.casefold()}"} or not limpio.endswith(f".{dominio.casefold()}"):
                continue
            nuevos.add(limpio)
    if not nuevos:
        return {"senal": "subdominio nuevo", "nivel": "observado", "detalle": "crt.sh no muestra un subdominio nuevo en el período", "nombres": []}
    return {"senal": "subdominio nuevo", "nivel": "observado", "nombres": sorted(nuevos)}


def feeds_declarados(html: str | None, origen: str) -> list[str]:
    salida = []
    for etiqueta in _LINK.findall(html or ""):
        atributos = {k.lower(): (a or b) for k, a, b in _ATRIBUTO.findall(etiqueta)}
        if "alternate" in atributos.get("rel", "").lower() and atributos.get("type", "").lower() in TIPOS_FEED:
            href = atributos.get("href", "").strip()
            if href and "comments" not in href.lower():
                salida.append(urljoin(origen + "/", href))
    return list(dict.fromkeys(salida))


def fechas_de_feed(texto: str) -> list[date]:
    fechas = []
    for crudo in _PUBDATE.findall(texto or ""):
        try:
            fechas.append(parsedate_to_datetime(crudo).date())
        except (TypeError, ValueError):
            continue
    for crudo in _ISO.findall(texto or ""):
        try:
            fechas.append(date.fromisoformat(crudo))
        except ValueError:
            continue
    return fechas


def ultima_publicacion(html: str | None, origen: str, session=None, hoy: date | None = None) -> dict:
    """La fecha más reciente que declara el feed del blog. Sin feed legible, «no determinable»."""
    hoy = hoy or date.today()
    vacio = {"senal": "ultima publicacion", "nivel": "no determinable", "fecha": None, "url": None}
    if not origen:
        return vacio
    http = session or __import__("requests")
    candidatos = feeds_declarados(html, origen) or [origen + ruta for ruta in RUTAS_FEED]
    for url in candidatos[:3]:
        try:
            resp = http.get(url, headers=UA, timeout=20)
        except Exception:  # noqa: BLE001
            continue
        texto = str(getattr(resp, "text", "") or "")[:2_000_000]
        if getattr(resp, "status_code", 0) != 200 or not re.search(r"<(rss|feed)\b", texto[:3000], re.IGNORECASE):
            continue
        fechas = [f for f in fechas_de_feed(texto) if f <= hoy]
        if fechas:
            return {"senal": "ultima publicacion", "nivel": "observado", "fecha": max(fechas).isoformat(), "url": url}
    return vacio


def vacante(html: str | None) -> dict:
    if html is None:
        return {"senal": "vacante", "nivel": "no determinable", "detalle": "no se revisó una página de empleo"}
    plano = html.casefold()
    if "vacante" in plano and any(area in plano for area in ("marketing", "seo", "contenido")):
        return {"senal": "vacante", "nivel": "observado", "detalle": "la página trae vacante de marketing, SEO o contenido"}
    return {"senal": "vacante", "nivel": "no determinable", "detalle": "esa página no trae la vacante; no prueba que no exista"}


def pauta_activa(nota: str | None = None) -> dict:
    if str(nota or "").strip():
        return {"senal": "pauta activa", "nivel": "observado", "detalle": nota.strip()}
    return {
        "senal": "pauta activa",
        "nivel": "no determinable",
        "detalle": "la revisa Cristina a mano en la biblioteca de anuncios",
    }
