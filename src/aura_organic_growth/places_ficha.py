"""Una Text Search por lead. Solo se puede guardar el place_id.

La política de Google: no precargar, cachear ni almacenar contenido de
Places, salvo el place ID. Si una nota o las reseñas salen al prospecto
sin un mapa, llevan el logo de Google.
"""

from __future__ import annotations

import os

import requests

TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
CAMPOS = "places.id"
LOGO_SIN_MAPA = (
    "Si una nota o las reseñas de Places salen al prospecto sin mapa, "
    "llevan el logo de Google."
)
_GUARDABLE = ("status", "razon", "llamadas", "query", "place_id")


def ficha_google(empresa: str, ciudad: str = "", pais: str = "", session=None) -> dict:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        return {"status": "sin_dato", "razon": "sin GOOGLE_MAPS_API_KEY", "llamadas": 0}
    query = ", ".join(parte for parte in (empresa, ciudad, pais) if str(parte).strip())
    if not query:
        return {"status": "sin_dato", "razon": "sin nombre", "llamadas": 0}
    http = session or requests
    resp = http.post(
        TEXT_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": CAMPOS,
        },
        json={"textQuery": query, "languageCode": "es", "pageSize": 1},
        timeout=20,
    )
    if resp.status_code != 200:
        return {"status": "sin_dato", "razon": f"http_{resp.status_code}", "llamadas": 1, "query": query}
    places = (resp.json() or {}).get("places") or []
    if not places:
        return {"status": "sin_dato", "razon": "sin ficha", "llamadas": 1, "query": query}
    place_id = str(places[0].get("id") or "").replace("places/", "") or None
    return {"status": "ok", "llamadas": 1, "query": query, "place_id": place_id}


def ids_por_categoria(categoria: str, ciudad: str, pais: str = "", session=None) -> dict:
    """Una Text Search de la categoría en la ciudad. Solo place_id, sin ficha."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    categoria = str(categoria or "").strip()
    ciudad = str(ciudad or "").strip()
    if not categoria or not ciudad or categoria.casefold() == "sin dato":
        return {"status": "sin_dato", "razon": "sin categoría o sin ciudad", "llamadas": 0, "place_ids": []}
    if not api_key:
        return {"status": "sin_dato", "razon": "sin GOOGLE_MAPS_API_KEY", "llamadas": 0, "place_ids": []}
    query = ", ".join(parte for parte in (categoria, ciudad, pais) if parte)
    http = session or requests
    resp = http.post(
        TEXT_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": CAMPOS,
        },
        json={"textQuery": query, "languageCode": "es", "pageSize": 10},
        timeout=20,
    )
    if resp.status_code != 200:
        return {"status": "sin_dato", "razon": f"http_{resp.status_code}", "llamadas": 1, "place_ids": []}
    ids = []
    for place in (resp.json() or {}).get("places") or []:
        place_id = str(place.get("id") or "").replace("places/", "")
        if place_id:
            ids.append(place_id)
    return {"status": "ok", "llamadas": 1, "query": query, "place_ids": ids}


def para_guardar(resultado: dict) -> dict:
    """Tira nombre, dirección, nota y reseñas antes de escribir a disco."""
    return {clave: resultado[clave] for clave in _GUARDABLE if clave in resultado}
