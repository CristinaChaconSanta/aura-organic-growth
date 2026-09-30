"""Cliente mínimo de PostgREST. No crea tablas y no envía correo."""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

from aura_organic_growth.lead_intel import ORGANIC_ROOT

load_dotenv(ORGANIC_ROOT / ".env")


def configurado() -> tuple[str, dict]:
    url = os.environ["SUPABASE_URL"].strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    key = os.environ["SUPABASE_KEY"].strip()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    return url, headers


def pedir(method: str, ruta: str, **kwargs) -> requests.Response:
    base, headers = configurado()
    propios = kwargs.pop("headers", {})
    resp = requests.request(method, f"{base}{ruta}", headers={**headers, **propios}, timeout=40, **kwargs)
    return resp
