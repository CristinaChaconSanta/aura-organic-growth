"""Una Text Search por lead: la ficha de Google. Sin contexto de lugar.

No geocodifica, no busca vecinos, no calcula estrato ni competencia.
"""

from __future__ import annotations

import os

import requests

TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
CAMPOS = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.businessStatus",
        "places.websiteUri",
        "places.nationalPhoneNumber",
    ]
)


def ficha_google(empresa: str, ciudad: str = "", pais: str = "", session=None) -> dict:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        return {"status": "sin_dato", "razon": "sin GOOGLE_MAPS_API_KEY", "llamadas": 0}
    query = ", ".join(p for p in (empresa, ciudad, pais) if str(p).strip())
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
        return {"status": "sin_dato", "razon": f"http_{resp.status_code}", "llamadas": 1}
    places = (resp.json() or {}).get("places") or []
    if not places:
        return {"status": "sin_dato", "razon": "sin ficha", "llamadas": 1, "query": query}
    place = places[0]
    nombre = place.get("displayName") or {}
    return {
        "status": "ok",
        "llamadas": 1,
        "query": query,
        "place_id": (place.get("id") or "").replace("places/", "") or None,
        "name": nombre.get("text") if isinstance(nombre, dict) else nombre,
        "address": place.get("formattedAddress"),
        "rating": place.get("rating"),
        "resenas": place.get("userRatingCount"),
        "business_status": place.get("businessStatus"),
        "website": place.get("websiteUri"),
        "telefono": place.get("nationalPhoneNumber"),
    }
