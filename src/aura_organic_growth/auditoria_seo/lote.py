"""Auditoría SEO para muchos sitios: los rápidos primero, los grandes al final.

El tamaño se estima con las URLs del sitemap antes de rastrear. Un sitio que
se estima por encima del tope, o que se corta por tiempo en la primera
vuelta, pasa a la segunda vuelta y se retoma sin tope.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from aura_organic_growth.lote import es_pfs
from aura_organic_growth.observados import url_de

# Páginas por segundo medidas en Flamingo con concurrencia 3 y retardo 0,3 s,
# contando la verificación de enlaces. Criterio interno, no de Google.
RITMO = 1.3
TOPE_RAPIDO_S = 300


def sitios_de_fichas(filas: list[dict]) -> list[dict]:
    """Un sitio por dominio, con la ficha de mayor score. Sin web y PFS no entran."""
    mejor: dict[str, dict] = {}
    for fila in filas:
        lead = fila.get("leads") or {}
        empresa = str(lead.get("empresa") or "").strip()
        dominio = str(lead.get("dominio") or "").strip().lower().removeprefix("www.")
        url = url_de(str(lead.get("url") or "").strip(), dominio)
        if not url or es_pfs(empresa, dominio):
            continue
        clave = dominio or urlsplit(url).netloc.lower().removeprefix("www.")
        score = fila.get("score") or 0
        if clave in mejor and score <= mejor[clave]["score"]:
            continue
        mejor[clave] = {
            "lead_id": fila.get("lead_id"),
            "empresa": empresa or "sin dato",
            "pais": str(lead.get("pais") or "").strip() or "sin dato",
            "dominio": clave,
            "url": url,
            "score": score,
        }
    return sorted(mejor.values(), key=lambda s: -s["score"])


def sitios_de_seleccion(seleccion: list[dict]) -> list[dict]:
    salida = []
    for lead in seleccion:
        url = url_de(str(lead.get("url") or "").strip(), str(lead.get("dominio") or ""))
        if url:
            salida.append({**lead, "url": url})
    return salida


def estimar_segundos(urls_sitemap: int | None) -> int | None:
    """Sin sitemap legible, None: el sitio va a la primera vuelta con tope."""
    if not urls_sitemap:
        return None
    return round(urls_sitemap / RITMO)


def ordenar(sitios: list[dict], tope: int = TOPE_RAPIDO_S) -> tuple[list[dict], list[dict]]:
    """(rápidos, grandes). Los grandes, del más chico al más grande."""
    rapidos = [s for s in sitios if s.get("estimado_s") is None or s["estimado_s"] <= tope]
    grandes = [s for s in sitios if s.get("estimado_s") is not None and s["estimado_s"] > tope]
    return rapidos, sorted(grandes, key=lambda s: s["estimado_s"])


def incompleto(resumen: dict | None) -> bool:
    """Se retoma el rastreo si se cortó o cubrió menos del 95 %. El cliente no sale del análisis."""
    if not resumen:
        return True
    cobertura = resumen.get("cobertura_sitemap")
    sin_sitemap = not resumen.get("urls_en_sitemap")
    return bool(resumen.get("cortado_por_tiempo")) or (not sin_sitemap and (cobertura or 0) < 0.95)


def fila_resumen(sitio: dict, resumen: dict | None, *, vuelta: int, error: str = "") -> dict:
    fila = {
        "empresa": sitio.get("empresa", "sin dato"),
        "dominio": sitio.get("dominio") or urlsplit(sitio["url"]).netloc,
        "url": sitio["url"],
        "vuelta": vuelta,
        "estimado_s": sitio.get("estimado_s"),
        "estado": "error" if error else "incompleto" if incompleto(resumen) else "completo",
        "en_analisis": True,
        "error": error,
    }
    if resumen:
        fila.update({
            "plataforma": resumen.get("plataforma"),
            "urls_en_sitemap": resumen.get("urls_en_sitemap"),
            "paginas_rastreadas": resumen.get("paginas_rastreadas"),
            "cobertura_sitemap": resumen.get("cobertura_sitemap"),
            "duracion_s": resumen.get("duracion_s"),
            "hallazgos": {h["id"]: h["afectadas"] for h in resumen.get("hallazgos") or []},
        })
    return fila
