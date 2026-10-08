"""Selecciona el lote, anota la madurez y mide a todo lead con web.

La madurez no descarta. Primer paso: la prueba en vivo con IA y la lectura del
sitio para IA. Después, velocidad, búsquedas, la portada y la auditoría SEO del mismo sitio.
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
from aura_organic_growth.ia import clave_gemini, consultar as consultar_ia, hallazgos_de_ia, servicio_de_sitio  # noqa: E402
from aura_organic_growth.oferta import evidencia as evidencia_de, oferta as oferta_de  # noqa: E402
from aura_organic_growth.legibilidad_ia import hallazgos_de_legibilidad, medir as medir_legibilidad  # noqa: E402
from aura_organic_growth.lote import descargar_fichas, guardar, seleccionar  # noqa: E402
from aura_organic_growth.analisis import siempre, unir  # noqa: E402
from aura_organic_growth.auditoria_seo.ejecutar import auditar  # noqa: E402
from aura_organic_growth.auditoria_seo.lote import TOPE_RAPIDO_S  # noqa: E402
from aura_organic_growth.cruce import idioma_de  # noqa: E402
from aura_organic_growth.madurez import clasificar  # noqa: E402
from aura_organic_growth.observados import de as observado_de, url_de  # noqa: E402
from aura_organic_growth.oportunidades import de_paginas, desde_respuesta  # noqa: E402
from aura_organic_growth.paginas import faltan  # noqa: E402
from aura_organic_growth.places_ficha import ficha_google, ids_por_categoria, para_guardar  # noqa: E402
from aura_organic_growth.senales import pauta_activa, subdominios_nuevos, ultima_publicacion, vacante, wayback  # noqa: E402
from aura_organic_growth.serp import encolar  # noqa: E402

HOY = date.today().isoformat()
# La respuesta de una IA cambia entre corridas: tres dan «en X de 3». ChatGPT cuesta USD 0,004 cada una.
REPETICIONES_IA = 3
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


def servicio_y_ciudad(lead: dict, dominio: str, html: str | None) -> tuple[list[str], str, str]:
    """Servicio observado por Cristina; si no, el texto literal de la portada. Ciudad guardada, o solo el país."""
    observado = observado_de(dominio)
    if observado:
        return observado["servicios"], observado["ciudad"], "observados"
    hallado = servicio_de_sitio(html, empresa=lead["empresa"], dominio=dominio, ciudad=lead["ciudad"])
    return ([hallado["servicio"]] if hallado else []), lead["ciudad"], (hallado["campo"] if hallado else "sin dato")


def palabras_de_busqueda(dominio: str) -> list[str]:
    """Palabras por las que Google muestra el dominio, del último lote de Labs. Vacía si no hay."""
    archivos = sorted((ROOT / "data" / "lotes").glob("labs-lote-*.json"))
    if not archivos:
        return []
    for registro in json.loads(archivos[-1].read_text(encoding="utf-8")):
        if registro.get("dominio") == dominio:
            return [str(p.get("palabra") or "") for p in registro.get("palabras") or []]
    return []


def pregunta_del_lead(lead: dict, dominio: str, url: str, html: str | None) -> dict:
    """Observado por Cristina; si no, la pregunta que escribe Gemini y verifica oferta.py.

    Sin GEMINI_API_KEY queda el texto literal de la portada, como antes.
    """
    observado = observado_de(dominio)
    if observado or not clave_gemini():
        servicios, ciudad, origen = servicio_y_ciudad(lead, dominio, html)
        return {"servicios": servicios, "ciudad": ciudad, "origen": origen, "pregunta": None, "oferta": None}
    registro = _seguro(
        lambda: oferta_de(
            evidencia_de(html, url),
            empresa=lead["empresa"],
            dominio=dominio,
            ciudad=lead["ciudad"],
            pais=lead["pais"],
            palabras_busqueda=palabras_de_busqueda(dominio),
        ),
        {"status": "sin dato", "razon": "sin respuesta"},
    )
    if registro.get("status") != "ok":
        return {"servicios": [], "ciudad": lead["ciudad"], "origen": "sin dato", "pregunta": None, "oferta": registro}
    ciudad = registro.get("ciudad_pregunta")
    return {
        "servicios": [registro["termino"]],
        # Si la ciudad de la ficha es de otro país, la que muestra el sitio para ese país, o ninguna.
        "ciudad": "" if ciudad in (None, "sin dato") else ciudad,
        "origen": "oferta",
        "pregunta": registro["preguntas"][0],
        "oferta": registro,
    }


def _paso_ia(
    lead: dict, url: str, html: str | None, repeticiones: int = REPETICIONES_IA
) -> tuple[dict, dict, list[dict]]:
    """Primer paso de la medición: prueba con IA y lectura del sitio para IA. Sin web no corre."""
    # El dominio guardado decide el cruce por marca; la url puede ser el sitio real (ver observados.URLS).
    dominio = lead["dominio"] or urlparse(_origen(url, "")).netloc.removeprefix("www.")
    elegida = pregunta_del_lead(lead, dominio, url, html)
    oferta = elegida["oferta"]
    if oferta and oferta.get("status") != "ok":
        ia = {
            "dominio": dominio, "status": "sin dato", "motores": [], "oferta": oferta,
            "razon": f"pregunta no confiable: {oferta.get('razon')}",
        }
    else:
        ia = _seguro(
            lambda: consultar_ia(
                elegida["servicios"],
                ciudad=elegida["ciudad"],
                pais=lead["pais"],
                dominio=dominio,
                empresa=lead["empresa"],
                origen_servicio=elegida["origen"],
                repeticiones=repeticiones,
                pregunta=elegida["pregunta"],
            ),
            {"dominio": dominio, "status": "sin dato", "razon": "sin respuesta", "motores": []},
        )
        if oferta:
            ia["oferta"] = oferta
    legibilidad = _seguro(
        lambda: medir_legibilidad(url, html=html),
        {"url": "sin dato", "fecha": HOY, "robots": {}, "llms_txt": None, "render": "no determinable"},
    )
    idioma = "pt-BR" if idioma_de(lead["pais"]) == "pt-BR" else "es"
    hallazgos = hallazgos_de_ia(ia, empresa=lead["empresa"]) + hallazgos_de_legibilidad(legibilidad, idioma=idioma)
    return ia, legibilidad, hallazgos


def _medir(lead: dict) -> dict:
    url = url_de(lead["url"], lead["dominio"])
    estado, html = _portada(url)
    tiene_web = bool(url)
    ia, legibilidad, hallazgos_ia = _paso_ia(lead, url, html) if tiene_web else ({}, {}, [])
    feed = (
        _seguro(lambda: ultima_publicacion(html, _origen(url, lead["dominio"])), {"senal": "ultima publicacion", "nivel": "no determinable"})
        if html else {"senal": "ultima publicacion", "nivel": "no determinable"}
    )
    madurez = clasificar(
        html if estado else None, tiene_web=tiene_web, llms_txt=legibilidad.get("llms_txt"), ultima_publicacion=feed
    )
    fila = {
        "empresa": lead["empresa"],
        "pais": lead["pais"],
        "ciudad": lead["ciudad"],
        "score": lead["score"],
        "url": url,
        "dominio": lead["dominio"],
        "en_analisis": True,
        "madurez": madurez["madurez"],
        "ruta": madurez["ruta"],
        "evidencia_madurez": madurez["evidencia"],
        "ultima_publicacion": feed,
    }
    if tiene_web:
        fila.update({"ia": ia, "legibilidad_ia": legibilidad, "hallazgos": cinco(hallazgos_ia)})
    if madurez["ruta"] != "auditar":
        # Sin web no hay sitio que medir. Con web la madurez no corta esta función.
        fila["problema"] = (
            "derivar a landing" if madurez["ruta"] == "derivar a landing" else "sin auditar: la portada no respondió"
        )
        return fila
    origen = _origen(url, lead["dominio"])
    hallazgos = list(hallazgos_ia)
    if estado and estado >= 400:
        hallazgos.append({
            "texto": f"La portada respondió HTTP {estado} el {HOY}.",
            "consecuencia": "Quien entra no llega a ver la oferta.",
            "alcance": "sitio",
            "tipo": "error",
            "nivel": "observado",
        })
    if estado is not None:
        hallazgos.extend(de_paginas([desde_respuesta(url, estado, html or "")]))
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
    return unir(fila)


def _auditar_junto(url: str) -> dict:
    """El profundo entra en la misma medición. Si hoy ya quedó completo, no se rastrea otra vez."""
    return auditar(url, tiempo_max=TOPE_RAPIDO_S, reusar=True)


def main() -> None:
    base, headers = _headers_supabase()
    filas = descargar_fichas(lambda offset, tamano: _pagina(base, headers, offset, tamano), tamano=30)
    lote = seleccionar(filas)
    guardar(lote)
    vistos: set[tuple[str, str]] = set()
    resumen = []
    for lead in lote:
        fila = siempre(_medir(lead), _auditar_junto)
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
