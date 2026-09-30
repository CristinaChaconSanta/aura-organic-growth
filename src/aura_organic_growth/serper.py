"""Búsquedas comerciales en Serper. No usa la cola de DataForSEO.

Sin SERPER_API_KEY queda «sin dato». Máximo 10 consultas, y solo si hay
servicio y ciudad observados. gl y hl salen del país guardado.
"""

from __future__ import annotations

import os
import re
from datetime import date

from aura_organic_growth.cruce import dominio_de, plano
from aura_organic_growth.serp import armar_consultas

URL = "https://google.serper.dev/search"
FUENTE = "Serper"
TOPE = 10
AUSENTE = "no aparece en el top 10"
MERCADOS = {
    "chile": {"gl": "cl", "hl": "es"},
    "mexico": {"gl": "mx", "hl": "es"},
    "brasil": {"gl": "br", "hl": "pt"},
    "brazil": {"gl": "br", "hl": "pt"},
}
_LISTA = re.compile(
    r"mejores\s+(?:agencias|empresas)|melhores\s+(?:ag[eê]ncias|empresas)|best\s+(?:agencies|companies)",
    re.IGNORECASE,
)


def mercado_de(pais: str) -> dict | None:
    return MERCADOS.get(plano(pais))


def consultas_de(servicios: list[str], ciudad: str) -> list[dict]:
    return armar_consultas(servicios, ciudad)[:TOPE]


def es_lista(titulo: str) -> bool:
    return bool(_LISTA.search(titulo or ""))


def _posicion(organic: list[dict], dominio: str) -> int | str:
    propio = dominio_de(dominio)
    for indice, item in enumerate(organic, start=1):
        host = dominio_de(str(item.get("link") or ""))
        if host == propio:
            posicion = item.get("position")
            return posicion if isinstance(posicion, int) else indice
    return AUSENTE


def _dominios(organic: list[dict]) -> list[str]:
    vistos = []
    ya = set()
    for item in organic:
        host = dominio_de(str(item.get("link") or ""))
        if not host or host in ya:
            continue
        ya.add(host)
        vistos.append(host)
    return vistos


def _aparece(html: str, dominio: str) -> bool:
    return dominio_de(dominio) in (html or "").casefold()


def _lista(http, item: dict, dominio: str) -> dict | None:
    titulo = str(item.get("title") or "").strip()
    if not es_lista(titulo):
        return None
    url = str(item.get("link") or "").strip()
    if not url.startswith("http"):
        return {"titulo": titulo, "url": url, "aparece": None}
    resp = http.get(url, timeout=20, headers={"User-Agent": "AuraOrganicGrowth/1.0 (diagnostico)"})
    if getattr(resp, "status_code", 0) != 200:
        return {"titulo": titulo, "url": url, "aparece": None}
    return {"titulo": titulo, "url": url, "aparece": _aparece(getattr(resp, "text", "")[:500_000], dominio)}


def buscar(
    servicios: list[str],
    *,
    ciudad: str,
    pais: str,
    dominio: str,
    session=None,
    hoy: date | None = None,
) -> dict:
    fecha = (hoy or date.today()).isoformat()
    mercado = mercado_de(pais)
    consultas = consultas_de(servicios, ciudad)
    base = {"fecha": fecha, "pais": pais or "sin dato", "fuente": FUENTE, "consultas": []}
    if not mercado:
        return {**base, "status": "sin dato", "razon": "pais sin mercado de Serper"}
    if not consultas:
        return {**base, "status": "sin dato", "razon": "sin servicio o sin ciudad observados"}
    key = os.getenv("SERPER_API_KEY", "").strip()
    if not key:
        return {**base, "status": "sin dato", "razon": "sin SERPER_API_KEY"}
    http = session or __import__("requests")
    hechas = []
    for item in consultas:
        resp = http.post(
            URL,
            json={"q": item["consulta"], "num": 10, **mercado},
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            timeout=40,
        )
        if resp.status_code != 200:
            hechas.append({
                **item,
                "fecha": fecha,
                "pais": pais or "sin dato",
                "posicion": "sin dato",
                "dominios": [],
                "listas": [],
                "razon": f"http_{resp.status_code}",
            })
            continue
        organic = (resp.json() or {}).get("organic") or []
        listas = []
        for resultado in organic:
            lista = _lista(http, resultado, dominio)
            if lista:
                listas.append(lista)
        hechas.append({
            **item,
            "fecha": fecha,
            "pais": pais or "sin dato",
            "posicion": _posicion(organic, dominio),
            "dominios": _dominios(organic),
            "listas": listas,
        })
    return {**base, "gl": mercado["gl"], "hl": mercado["hl"], "status": "ok", "consultas": hechas}


def hallazgos_de_busqueda(registro: dict | None) -> list[dict]:
    if not registro or registro.get("status") != "ok":
        return []
    salida = []
    for consulta in registro.get("consultas") or []:
        fecha = consulta.get("fecha") or registro.get("fecha") or "sin dato"
        pais = consulta.get("pais") or registro.get("pais") or "sin dato"
        texto_consulta = consulta.get("consulta") or ""
        if consulta.get("posicion") == AUSENTE and texto_consulta:
            dominios = ", ".join(consulta.get("dominios") or []) or "sin dominios"
            salida.append({
                "texto": f"En «{texto_consulta}» ({pais}, {fecha}) no aparece en el top 10.",
                "evidencia": dominios,
                "fuente": FUENTE,
                "fecha": fecha,
                "nivel": "observado",
                "consecuencia": "Quien busca ese servicio en esa ciudad no lo encuentra en la primera página.",
            })
        for lista in consulta.get("listas") or []:
            if lista.get("aparece") is None or not lista.get("titulo"):
                continue
            cita = "sí cita" if lista["aparece"] else "no cita"
            salida.append({
                "texto": (
                    f"El artículo «{lista['titulo']}» {cita} el dominio. "
                    "Las IAs citan estas listas."
                ),
                "evidencia": str(lista.get("url") or ""),
                "fuente": FUENTE,
                "fecha": fecha,
                "nivel": "observado",
                "consecuencia": "Quien pregunta a una IA puede recibir esa lista en lugar del sitio.",
            })
    return salida
