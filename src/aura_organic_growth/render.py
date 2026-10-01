"""Ausencias que entran a la ficha salen de la página renderizada.

El HTML crudo no decide. Una sola sesión de Chrome recorre el lote.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

PRECIO = re.compile(r"(?:US\$|USD|\$)\s?\d[\d.,]*", re.I)
ID_FINAL = re.compile(r"-\d{6,}$")
RUIDO = {
    "apartamentos", "venta", "renta", "miami", "florida", "street", "drive",
    "ave", "avenue", "dr", "st", "ne", "nw", "se", "sw", "en", "the", "of",
}


def es_ficha(url: str) -> bool:
    partes = [p for p in urlparse(url).path.split("/") if p]
    return len(partes) >= 2 and bool(ID_FINAL.search(partes[-1]))


def _tokens_direccion(url: str) -> list[str]:
    slug = [p for p in urlparse(url).path.split("/") if p][-1]
    slug = ID_FINAL.sub("", slug)
    return [t for t in slug.split("-") if len(t) > 2 and t not in RUIDO]


def comprobar_lote(urls: list[str]) -> list[dict]:
    from playwright.sync_api import sync_playwright

    filas = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page()
        for url in urls:
            filas.append(_una(page, url))
        browser.close()
    return filas


def _una(page, url: str) -> dict:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        # El listado de PFS pinta título y H1 después del HTML. Se espera a que aparezcan.
        page.wait_for_function(
            "() => (document.title || '').trim().length > 0 && document.querySelectorAll('h1').length > 0",
            timeout=8000,
        )
    except Exception as exc:  # noqa: BLE001
        error = type(exc).__name__
    else:
        error = ""

    title = ""
    h1: list[str] = []
    meta = ""
    texto = ""
    try:
        title = (page.title() or "").strip()
        h1 = [t.strip() for t in page.locator("h1").all_text_contents() if t.strip()]
        meta = page.locator('meta[name="description"]').first.get_attribute("content") or ""
        meta = meta.strip()
        texto = page.locator("body").inner_text(timeout=5000)
    except Exception as exc:  # noqa: BLE001
        error = error or type(exc).__name__

    ficha = es_ficha(url)
    tokens = _tokens_direccion(url) if ficha else []
    cuerpo = texto.lower()
    direccion = bool(tokens) and all(t.lower() in cuerpo for t in tokens[:3])
    precio = bool(PRECIO.search(texto)) if ficha else None

    ausencias = []
    if not title:
        ausencias.append("title")
    if not h1:
        ausencias.append("h1")
    if not meta:
        ausencias.append("meta_description")
    if ficha and not direccion:
        ausencias.append("direccion")
    if ficha and not precio:
        ausencias.append("precio")

    return {
        "url": url,
        "ficha": ficha,
        "title": title,
        "h1": h1[:3],
        "meta_description": meta[:180],
        "direccion_visible": direccion if ficha else None,
        "precio_visible": precio,
        "ausencias_render": ausencias,
        "error": error,
    }


def paginas_renderizadas(urls: list[str]) -> dict[str, dict | None]:
    """Palabras visibles y HTML ya renderizado. None si Chrome o la página no responden."""
    salida: dict[str, dict | None] = {url: None for url in urls}
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page()
            for url in urls:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:  # noqa: BLE001
                        pass
                    texto = page.locator("body").inner_text(timeout=5000)
                    salida[url] = {"palabras": len(re.findall(r"\w+", texto)), "html": page.content()}
                except Exception:  # noqa: BLE001
                    salida[url] = None
            browser.close()
    except Exception:  # noqa: BLE001
        return {url: None for url in urls}
    return salida
