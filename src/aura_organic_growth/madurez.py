"""Madurez digital antes de auditar. Baja o sin web no entra a la auditoría."""

from __future__ import annotations

import re
from datetime import date, datetime

_CRM = (
    "hs-scripts.com", "js.hs-analytics", "hubspot", "salesforce", "pardot",
    "pipedrive", "zoho", "rdstation", "activecampaign",
)
_ANALITICA = (
    "googletagmanager.com", "gtag(", "google-analytics.com", "plausible.io",
    "hotjar.com", "clarity.ms", "matomo",
)
_PAUTA = ("fbevents.js", "connect.facebook.net", "googleadservices.com", "gtag('config', 'aw-")
_FECHA = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")


def _plano(html: str) -> str:
    return html.casefold()


def _tiene(html: str, marcas: tuple[str, ...]) -> str | None:
    plano = _plano(html)
    for marca in marcas:
        if marca in plano:
            return marca
    return None


def _fecha_reciente(html: str, hoy: date, dias: int = 183) -> str | None:
    for anio, mes, dia in _FECHA.findall(html):
        try:
            encontrada = date(int(anio), int(mes), int(dia))
        except ValueError:
            continue
        if 0 <= (hoy - encontrada).days <= dias:
            return encontrada.isoformat()
    return None


def clasificar(html: str | None, *, hoy: date | None = None, tiene_web: bool = True) -> dict:
    """La evidencia es la marca encontrada. Sin web, o sin ninguna señal, no se audita."""
    hoy = hoy or date.today()
    if not tiene_web:
        return {
            "madurez": "sin web",
            "ruta": "derivar a landing",
            "evidencia": [{"senal": "sitio", "nivel": "observado", "detalle": "no hay url"}],
        }
    if html is None:
        return {
            "madurez": "no determinable",
            "ruta": "no auditar",
            "evidencia": [{"senal": "sitio", "nivel": "no determinable", "detalle": "la portada no respondió"}],
        }
    evidencia = []
    crm = _tiene(html, _CRM)
    if crm:
        evidencia.append({"senal": "crm", "nivel": "observado", "detalle": crm})
    analitica = _tiene(html, _ANALITICA)
    if analitica:
        evidencia.append({"senal": "analitica", "nivel": "observado", "detalle": analitica})
    pauta = _tiene(html, _PAUTA)
    if pauta:
        evidencia.append({"senal": "etiqueta de pauta", "nivel": "observado", "detalle": pauta})
    blog = _fecha_reciente(html, hoy)
    if blog:
        evidencia.append({"senal": "blog activo", "nivel": "observado", "detalle": blog})
    elif "/blog" in _plano(html):
        evidencia.append({
            "senal": "blog",
            "nivel": "no determinable",
            "detalle": "hay enlace a blog y no hay fecha de los últimos 6 meses",
        })
    senales = {item["senal"] for item in evidencia if item["nivel"] == "observado"}
    if len(senales) >= 2:
        madurez = "alta"
    elif len(senales) == 1:
        madurez = "media"
    else:
        madurez = "baja"
    ruta = "auditar" if madurez in ("media", "alta") else "derivar a landing"
    return {"madurez": madurez, "ruta": ruta, "evidencia": evidencia or [
        {"senal": "crm, pauta, analitica, blog", "nivel": "observado", "detalle": "ninguna en la portada"},
    ]}


def fecha_de_hoy(valor: str | None = None) -> date:
    if not valor:
        return date.today()
    return datetime.strptime(valor, "%Y-%m-%d").date()
