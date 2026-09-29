"""Datos de usuarios reales. Sin registro: «sin datos de campo», nunca «está bien»."""

from __future__ import annotations

import os

CRUX_URL = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
PSI_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
SIN_CAMPO = "sin datos de campo"


def _key() -> str:
    return os.getenv("CRUX_API_KEY", "").strip() or os.getenv("PAGESPEED_API_KEY", "").strip()


def hallazgo_velocidad(medicion: dict, fecha: str) -> dict | None:
    """Solo entra si hay un LCP de campo peor que el umbral bueno de Google."""
    if medicion.get("lcp_ms") is None:
        return None
    segundos = medicion["lcp_ms"] / 1000
    if segundos <= 2.5:
        return None
    umbral = "Google marca por encima de 4 s como lento." if segundos > 4 else "Google marca por encima de 2,5 s como mejorable."
    fuente = medicion.get("fuente") or "campo"
    return {
        "texto": f"El origen carga el contenido principal en {segundos:.1f} s para usuarios reales ({fuente}, {fecha}). {umbral}",
        "consecuencia": "Quien entra desde el celular espera antes de ver la página.",
        "alcance": "sitio",
        "tipo": "velocidad",
        "nivel": "observado",
    }


def _lcp(percentil) -> dict:
    if percentil is None:
        return {"lcp": SIN_CAMPO, "nivel": "no determinable"}
    return {"lcp_ms": int(percentil), "nivel": "observado", "fuente": "campo"}


def campo(origen: str, session=None, form_factor: str = "PHONE") -> dict:
    """Consulta el origen en CrUX. Si la API no está, mira solo el campo de PageSpeed."""
    if not origen:
        return {"lcp": SIN_CAMPO, "nivel": "no determinable", "razon": "sin origen"}
    key = _key()
    if not key:
        return {"lcp": SIN_CAMPO, "nivel": "no determinable", "razon": "sin CRUX_API_KEY"}
    http = session or __import__("requests")
    resp = http.post(
        f"{CRUX_URL}?key={key}",
        json={"origin": origen, "formFactor": form_factor},
        timeout=30,
    )
    if resp.status_code == 404:
        return {"lcp": SIN_CAMPO, "nivel": "observado", "razon": "la API no tiene registro de este origen"}
    if resp.status_code == 200:
        metrics = ((resp.json() or {}).get("record") or {}).get("metrics") or {}
        p75 = ((metrics.get("largest_contentful_paint") or {}).get("percentiles") or {}).get("p75")
        return {**_lcp(p75), "form_factor": form_factor}
    psi = http.get(PSI_URL, params={"url": origen, "strategy": "mobile", "category": "performance", "key": key}, timeout=60)
    if psi.status_code != 200:
        return {"lcp": SIN_CAMPO, "nivel": "no determinable", "razon": f"http_{resp.status_code}"}
    experiencia = (psi.json() or {}).get("loadingExperience") or {}
    percentil = ((experiencia.get("metrics") or {}).get("LARGEST_CONTENTFUL_PAINT_MS") or {}).get("percentile")
    if percentil is None:
        return {"lcp": SIN_CAMPO, "nivel": "observado", "razon": "PageSpeed no trajo datos de campo"}
    return {**_lcp(percentil), "fuente": "campo vía PageSpeed", "form_factor": "mobile"}
