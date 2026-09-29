"""Knowledge Graph Search API: si Google devuelve la marca como entidad.

Sin key, o sin un nombre que coincida, no se afirma que Google no la reconoce.
"""

from __future__ import annotations

import os

KG_URL = "https://kgsearch.googleapis.com/v1/entities:search"


def _plano(texto: str) -> str:
    return (
        texto.casefold()
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )


def entidad(marca: str, session=None, idioma: str = "es") -> dict:
    marca = str(marca or "").strip()
    key = os.getenv("KNOWLEDGE_GRAPH_API_KEY", "").strip()
    if not marca:
        return {"status": "sin dato", "nivel": "no determinable", "razon": "sin marca"}
    if not key:
        return {"status": "sin dato", "nivel": "no determinable", "razon": "sin KNOWLEDGE_GRAPH_API_KEY"}
    http = session or __import__("requests")
    resp = http.get(
        KG_URL,
        params={"query": marca, "key": key, "limit": 5, "languages": idioma},
        timeout=20,
    )
    if resp.status_code != 200:
        return {"status": "sin dato", "nivel": "no determinable", "razon": f"http_{resp.status_code}"}
    items = ((resp.json() or {}).get("itemListElement") or [])
    buscada = _plano(marca)
    for item in items:
        result = item.get("result") or {}
        nombre = str(result.get("name") or "")
        if buscada and buscada in _plano(nombre):
            return {
                "status": "ok",
                "nivel": "observado",
                "nombre": nombre,
                "id": result.get("@id"),
            }
    if not items:
        return {
            "status": "sin dato",
            "nivel": "observado",
            "razon": "la API no devolvió entidades para esta consulta",
        }
    return {
        "status": "sin dato",
        "nivel": "no determinable",
        "razon": "la API devolvió entidades y ninguna coincide con la marca",
    }
