"""Arma la fila de staging. No redacta y no envía.

Los hallazgos salen de la medición. Si no hay nivel observado, inferido
o estimado, la lista queda vacía y no se inventa uno.
"""

from __future__ import annotations

import re

from aura_organic_growth.cruce import contacto_del_dominio, dominio_de, idioma_de
from aura_organic_growth.labs import hallazgo_bolsas, hallazgo_de_labs
from aura_organic_growth.serper import hallazgos_de_busqueda

NIVELES = ("observado", "inferido", "estimado")
_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")


def _fecha_en(texto: str, respaldo: str) -> str:
    hallada = _FECHA.search(texto or "")
    return hallada.group(0) if hallada else respaldo


def hallazgos_de_medicion(medicion: dict | None, fecha: str) -> list[dict]:
    if not medicion:
        return []
    velocidad = medicion.get("velocidad") or {}
    salida = []
    for item in medicion.get("hallazgos") or []:
        nivel = item.get("nivel")
        texto = str(item.get("texto") or "").strip()
        if nivel not in NIVELES or not texto:
            continue
        evidencia = texto
        if item.get("tipo") == "velocidad" and velocidad.get("lcp_ms") is not None:
            evidencia = f"LCP {int(velocidad['lcp_ms'])} ms. {texto}"
        fuente = str(item.get("fuente") or "").strip()
        if item.get("tipo") == "velocidad" and velocidad.get("fuente"):
            fuente = str(velocidad["fuente"])
        salida.append({
            "texto": texto,
            "evidencia": evidencia,
            "fuente": fuente or "sin dato",
            "fecha": str(item.get("fecha") or _fecha_en(texto, fecha)),
            "nivel": nivel,
            "consecuencia": str(item.get("consecuencia") or "").strip(),
        })
    for hallazgo in (
        hallazgo_de_labs(medicion.get("labs")),
        hallazgo_bolsas(medicion.get("labs")),
    ):
        if hallazgo:
            salida.append(hallazgo)
    salida.extend(hallazgos_de_busqueda(medicion.get("serper")))
    wayback = medicion.get("wayback") or {}
    detalle = str(wayback.get("detalle") or "").strip()
    if wayback.get("nivel") in NIVELES and detalle:
        salida.append({
            "texto": detalle,
            "evidencia": detalle,
            "fuente": "Wayback CDX",
            "fecha": _fecha_en(detalle, fecha),
            "nivel": wayback["nivel"],
        })
    return salida


def juntar(resumen: dict | None, labs: dict | None, serper: dict | None) -> dict:
    base = dict(resumen or {})
    if labs:
        base["labs"] = labs
    if serper:
        base["serper"] = serper
    return base


def parche_pendiente(hallazgos: list[dict]) -> dict | None:
    """Solo se reescribe una fila que ya tiene al menos un hallazgo."""
    if not hallazgos:
        return None
    return {"hallazgos": hallazgos, "estado": "pendiente"}


def fila_staging(
    lead: dict,
    medicion: dict | None,
    contactos: list[dict],
    *,
    hipotesis: str,
    fecha: str,
) -> dict:
    dominio = dominio_de(str(lead.get("dominio") or lead.get("url") or ""))
    return {
        "lead_id": lead["lead_id"],
        "empresa": lead.get("empresa") or "sin dato",
        "dominio": dominio,
        "pais": lead.get("pais") or "sin dato",
        "contacto": contacto_del_dominio(dominio, contactos) or {
            "nombre": None,
            "cargo": None,
            "email": None,
            "email_status": None,
            "precaucion": None,
        },
        "idioma": idioma_de(str(lead.get("pais") or "")),
        "hallazgos": hallazgos_de_medicion(medicion, fecha),
        "borrador": "",
        "estado": "pendiente",
        "hipotesis": hipotesis,
        "tipo_apertura": None,
        "cta": None,
        "industria": lead.get("industria") or "sin dato",
        "fecha_envio": None,
        "fecha_reunion": None,
    }


def armar_lote(
    seleccion: list[dict],
    mediciones: dict[str, dict],
    contactos: list[dict],
    *,
    hipotesis: str,
    fecha: str,
) -> list[dict]:
    filas = []
    for lead in seleccion:
        dominio = dominio_de(str(lead.get("dominio") or lead.get("url") or ""))
        filas.append(fila_staging(
            lead,
            mediciones.get(dominio),
            contactos,
            hipotesis=hipotesis,
            fecha=fecha,
        ))
    return filas
