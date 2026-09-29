"""Selecciona el lote, clasifica la madurez y mide solo media o alta.

Guarda país, place_id y el problema más grave. No guarda contenido de Places.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from aura_organic_growth.competidores import comparar_velocidad, repetidos  # noqa: E402
from aura_organic_growth.crux import campo, hallazgo_velocidad  # noqa: E402
from aura_organic_growth.entidad import entidad  # noqa: E402
from aura_organic_growth.hallazgos import cinco, problema_mas_grave  # noqa: E402
from aura_organic_growth.lote import descargar_fichas, guardar, seleccionar  # noqa: E402
from aura_organic_growth.madurez import clasificar  # noqa: E402
from aura_organic_growth.paginas import faltan  # noqa: E402
from aura_organic_growth.places_ficha import ficha_google, ids_por_categoria, para_guardar  # noqa: E402
from aura_organic_growth.senales import pauta_activa, subdominios_nuevos, vacante, wayback  # noqa: E402
from aura_organic_growth.serp import encolar  # noqa: E402

HOY = date.today().isoformat()
UA = {"User-Agent": "AuraOrganicGrowth/1.0 (diagnostico)"}


def _headers_supabase() -> tuple[str, dict]:
    url = os.environ["SUPABASE_URL"].rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    key = os.environ["SUPABASE_KEY"]
    headers = {"apikey": key, "Accept": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    return url, headers


def _pagina(base: str, headers: dict, offset: int, tamano: int) -> list:
    ultimo: Exception | None = None
    for intento in range(4):
        try:
            resp = requests.get(
                f"{base}/rest/v1/fichas",
                headers=headers,
                params={
                    "select": "score,fecha,lead_id,leads(empresa,pais,ciudad,url,dominio,industria)",
                    "order": "score.desc.nullslast",
                    "limit": str(tamano),
                    "offset": str(offset),
                },
                timeout=40,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except requests.RequestException as exc:
            ultimo = exc
            time.sleep(1.5 * (intento + 1))
    if ultimo:
        raise ultimo
    return []


def _origen(url: str, dominio: str) -> str:
    if url.startswith("http"):
        partes = urlparse(url)
        if partes.netloc:
            return f"{partes.scheme}://{partes.netloc}"
    if dominio:
        return f"https://{dominio}"
    return ""


def _portada(url: str) -> tuple[int | None, str | None]:
    if not url:
        return None, None
    try:
        resp = requests.get(url, headers=UA, timeout=20, allow_redirects=True)
    except requests.RequestException:
        return None, None
    return resp.status_code, resp.text[:200_000]


def _seguro(llamada, fallo: dict) -> dict:
    try:
        return llamada()
    except requests.RequestException:
        return fallo


def _medir(lead: dict) -> dict:
    url = lead["url"] or _origen("", lead["dominio"])
    estado, html = _portada(url)
    tiene_web = bool(url)
    madurez = clasificar(html if estado else None, tiene_web=tiene_web)
    fila = {
        "empresa": lead["empresa"],
        "pais": lead["pais"],
        "ciudad": lead["ciudad"],
        "score": lead["score"],
        "madurez": madurez["madurez"],
        "ruta": madurez["ruta"],
        "evidencia_madurez": madurez["evidencia"],
    }
    if madurez["ruta"] != "auditar":
        fila["problema"] = (
            "derivar a landing" if madurez["ruta"] == "derivar a landing" else "sin auditar: la portada no respondió"
        )
        return fila
    origen = _origen(url, lead["dominio"])
    hallazgos = []
    if estado and estado >= 400:
        hallazgos.append({
            "texto": f"La portada respondió HTTP {estado} el {HOY}.",
            "consecuencia": "Quien entra no llega a ver la oferta.",
            "alcance": "sitio",
            "tipo": "error",
            "nivel": "observado",
        })
    velocidad = _seguro(lambda: campo(origen), {"lcp": "sin datos de campo", "nivel": "no determinable", "razon": "sin respuesta"})
    hallazgo = hallazgo_velocidad(velocidad, HOY)
    if hallazgo:
        hallazgos.append(hallazgo)
    dominio = urlparse(origen).netloc.removeprefix("www.")
    fila.update({
        "place": para_guardar(_seguro(
            lambda: ficha_google(lead["empresa"], lead["ciudad"], lead["pais"]),
            {"status": "sin_dato", "razon": "sin respuesta", "llamadas": 0},
        )),
        "velocidad": {k: velocidad[k] for k in velocidad if k in ("lcp", "lcp_ms", "nivel", "fuente", "razon")},
        "entidad": _seguro(lambda: entidad(lead["empresa"]), {"status": "sin dato", "nivel": "no determinable"}),
        "wayback": _seguro(lambda: wayback(dominio), {"senal": "cambio de portada", "nivel": "no determinable"}),
        "subdominios": _seguro(lambda: subdominios_nuevos(dominio), {"senal": "subdominio nuevo", "nivel": "no determinable", "nombres": []}),
        "vacante": vacante(html),
        "pauta": pauta_activa(),
        "busquedas": encolar([], ciudad=lead["ciudad"], pais=lead["pais"]),
        "competidores": repetidos([]),
        "velocidad_vs_competidores": comparar_velocidad({"dominio": dominio, "lcp_ms": velocidad.get("lcp_ms")}, []),
        "paginas_que_faltan": faltan([], [], cobertura="portada"),
        "hallazgos": cinco(hallazgos),
    })
    fila["problema"] = problema_mas_grave(hallazgos)
    return fila


def main() -> None:
    base, headers = _headers_supabase()
    filas = descargar_fichas(lambda offset, tamano: _pagina(base, headers, offset, tamano), tamano=30)
    lote = seleccionar(filas)
    guardar(lote)
    vistos: set[tuple[str, str]] = set()
    resumen = []
    for lead in lote:
        fila = _medir(lead)
        if fila["ruta"] == "auditar":
            clave = (lead["industria"], lead["ciudad"])
            if clave not in vistos and lead["industria"] != "sin dato" and lead["ciudad"] != "sin dato":
                vistos.add(clave)
                fila["places_categoria"] = _seguro(
                    lambda: ids_por_categoria(lead["industria"], lead["ciudad"], lead["pais"]),
                    {"status": "sin_dato", "llamadas": 0, "place_ids": []},
                )
        resumen.append(fila)
        print(f"{fila['empresa']} ({fila['pais']}) — {fila['problema']}", flush=True)
    destino = ROOT / "data" / "lotes" / f"resumen-{HOY}.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
