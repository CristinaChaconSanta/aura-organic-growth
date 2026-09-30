"""DataForSEO Labs: palabras donde el dominio aparece, y con quién lo agrupa Google.

Chile, México y Brasil salen del país guardado en el lead. Sin credenciales
no hay llamada: queda «sin dato». El tráfico es estimado y se rotula así.
"""

from __future__ import annotations

import os
import re
from datetime import date

from aura_organic_growth.cruce import dominio_de, plano

RANKED = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"
COMPETITORS = "https://api.dataforseo.com/v3/dataforseo_labs/google/competitors_domain/live"
SALDO_URL = "https://api.dataforseo.com/v3/appendix/user_data"
SALDO_MINIMO = 0.10
FUENTE = "DataForSEO Labs"
MERCADOS = {
    "chile": {"location_code": 2152, "language_code": "es"},
    "mexico": {"location_code": 2484, "language_code": "es"},
    "brasil": {"location_code": 2076, "language_code": "pt"},
    "brazil": {"location_code": 2076, "language_code": "pt"},
}
REDES = frozenset({"instagram", "linkedin", "facebook", "youtube", "tiktok"})
_TOKEN = re.compile(r"[a-z0-9áéíóúñ]+", re.IGNORECASE)


def mercado_de(pais: str) -> dict | None:
    return MERCADOS.get(plano(pais))


def es_red_social(host: str) -> bool:
    limpio = dominio_de(host) or str(host or "").casefold().removeprefix("www.")
    return any(parte in REDES for parte in limpio.split("."))


def leer_saldo(data: dict) -> float | None:
    tareas = (data or {}).get("tasks") or []
    if not tareas:
        return None
    resultado = (tareas[0].get("result") or [None])[0] or {}
    balance = (resultado.get("money") or {}).get("balance")
    if isinstance(balance, (int, float)):
        return float(balance)
    return None


def _freno(http, auth) -> str | None:
    """None si se puede llamar. Antes de cada llamada de Labs."""
    resp = http.get(SALDO_URL, auth=auth, timeout=30)
    if getattr(resp, "status_code", 0) != 200:
        return "sin saldo"
    valor = leer_saldo(resp.json() or {})
    if valor is None:
        return "sin saldo"
    if valor < SALDO_MINIMO:
        return "saldo bajo USD 0.10"
    return None


def _credenciales() -> tuple[str, str]:
    return os.getenv("DATAFORSEO_LOGIN", "").strip(), os.getenv("DATAFORSEO_PASSWORD", "").strip()


def _vacio(dominio: str, pais: str, fecha: str, razon: str) -> dict:
    return {
        "dominio": dominio_de(dominio),
        "pais": pais or "sin dato",
        "fecha": fecha,
        "fuente": FUENTE,
        "status": "sin dato",
        "razon": razon,
        "palabras": [],
        "dominios": [],
        "truncado": False,
    }


def _tarea(data: dict) -> tuple[dict, str | None]:
    if not isinstance(data, dict):
        return {}, "respuesta vacia"
    tareas = data.get("tasks") or []
    tarea = tareas[0] if tareas else {}
    if tarea.get("status_code") != 20000:
        return {}, f"tarea_{tarea.get('status_code')}"
    resultado = (tarea.get("result") or [None])[0] or {}
    return resultado, None


def _trafico(valor, fecha: str) -> dict | None:
    if valor is None:
        return None
    return {"valor": valor, "etiqueta": "estimado", "fuente": FUENTE, "fecha": fecha}


def palabras_de(data: dict, fecha: str) -> tuple[list[dict], bool, str | None]:
    resultado, error = _tarea(data)
    if error:
        return [], False, error
    palabras = []
    for item in resultado.get("items") or []:
        serp = ((item.get("ranked_serp_element") or {}).get("serp_item") or {})
        if serp.get("type") not in (None, "organic"):
            continue
        palabra = str((item.get("keyword_data") or {}).get("keyword") or "").strip()
        posicion = serp.get("rank_group")
        if not palabra or not isinstance(posicion, int):
            continue
        fila = {"palabra": palabra, "posicion": posicion}
        trafico = _trafico(serp.get("etv"), fecha)
        if trafico:
            fila["trafico"] = trafico
        palabras.append(fila)
    total = resultado.get("total_count")
    truncado = isinstance(total, int) and total > len(palabras)
    return palabras, truncado, None


def dominios_de(data: dict, dominio_propio: str) -> tuple[list[dict], str | None]:
    resultado, error = _tarea(data)
    if error:
        return [], error
    propio = dominio_de(dominio_propio)
    vistos = []
    ya = set()
    for item in resultado.get("items") or []:
        host = dominio_de(str(item.get("domain") or ""))
        if not host or host == propio or host in ya or es_red_social(host):
            continue
        ya.add(host)
        intersecciones = item.get("intersections")
        fila = {"dominio": host}
        if isinstance(intersecciones, int):
            fila["intersecciones"] = intersecciones
        vistos.append(fila)
    vistos.sort(key=lambda fila: (-fila.get("intersecciones", 0), fila["dominio"]))
    return vistos, None


EMPLEO = frozenset({
    "empleo", "empleos", "trabalho", "trabalhos", "trabajar", "trabaje",
    "trabajo", "trabajos", "vacante", "vacantes", "vaga", "vagas",
    "emprego", "empregos", "postula", "postular", "reclutamiento",
    "trabalhe", "trabalhar", "creator", "creador", "creadores",
    "director", "direccion", "editor", "manager",
})
SERVICIO = frozenset({
    "agencia", "agencias", "publicidad", "publicidade", "seo", "sem",
    "branding", "marketing",
})


def _tokens(texto: str) -> set[str]:
    return {plano(token) for token in _TOKEN.findall(texto or "")}


def marcas_de(dominio: str) -> set[str]:
    etiquetas = dominio_de(dominio).split(".")
    return {plano(etiqueta) for etiqueta in etiquetas if len(plano(etiqueta)) >= 3}


def anotar_palabras(palabras: list[dict], dominio: str) -> list[dict]:
    marcas = marcas_de(dominio)
    anotadas = []
    for palabra in palabras:
        tokens = _tokens(str(palabra.get("palabra") or ""))
        tipos = []
        if tokens & EMPLEO:
            tipos.append("empleo")
        if tokens & marcas:
            tipos.append("marca")
        if tokens & SERVICIO:
            tipos.append("servicio")
        anotadas.append({**palabra, "tipos": tipos})
    return anotadas


def _citas(palabras: list[dict]) -> str:
    return ", ".join(f"«{item['palabra']}» (posición {item['posicion']})" for item in palabras[:3])


def hallazgo_de_labs(registro: dict | None) -> dict | None:
    """Solo si lo devuelto es empleo y marca, y no hay un servicio de agencia."""
    if not registro or registro.get("status") != "ok":
        return None
    palabras = anotar_palabras(registro.get("palabras") or [], str(registro.get("dominio") or ""))
    if not palabras:
        return None
    if any("servicio" in item["tipos"] for item in palabras):
        return None
    marcas = [item for item in palabras if "marca" in item["tipos"]]
    empleos = [item for item in palabras if "empleo" in item["tipos"]]
    if not marcas or not empleos:
        return None
    apertura = (
        "Entre las palabras mejor posicionadas que devolvió la fuente hay empleo y marca, no servicios de agencia."
        if registro.get("truncado")
        else "Aparece por empleo y por la marca, no por servicios de agencia."
    )
    texto = f"{apertura} Marca: {_citas(marcas)}. Empleo: {_citas(empleos)}."
    evidencia = "; ".join(
        f"{item['palabra']} posición {item['posicion']} ({', '.join(item['tipos']) or 'otra'})"
        for item in palabras
    )
    return {
        "texto": texto,
        "evidencia": evidencia,
        "fuente": FUENTE,
        "fecha": registro.get("fecha") or "sin dato",
        "nivel": "inferido",
        "alcance": "sitio",
        "tipo": "palabras",
        "consecuencia": "Quien busca una agencia no llega con estas palabras.",
    }


def adjuntar(mediciones: dict[str, dict], registros: list[dict]) -> dict[str, dict]:
    """Pega Labs por dominio. El nombre de la empresa no se usa."""
    salida = {dominio: dict(fila) for dominio, fila in mediciones.items()}
    for registro in registros:
        dominio = dominio_de(str(registro.get("dominio") or ""))
        if not dominio:
            continue
        base = dict(salida.get(dominio) or {})
        base["labs"] = registro
        salida[dominio] = base
    return salida


def consultar(
    dominio: str,
    pais: str,
    *,
    session=None,
    hoy: date | None = None,
    limite_palabras: int = 100,
    limite_dominios: int = 20,
) -> dict:
    fecha = (hoy or date.today()).isoformat()
    host = dominio_de(dominio)
    mercado = mercado_de(pais)
    if not host:
        return _vacio(dominio, pais, fecha, "sin dominio")
    if not mercado:
        return _vacio(host, pais, fecha, "pais sin mercado de Labs")
    login, password = _credenciales()
    if not login or not password:
        return _vacio(host, pais, fecha, "sin DATAFORSEO_LOGIN")
    http = session or __import__("requests")
    auth = (login, password)
    cuerpo_base = {"target": host, **mercado}
    freno = _freno(http, auth)
    if freno:
        return _vacio(host, pais, fecha, freno)
    ranked = http.post(
        RANKED,
        json=[{**cuerpo_base, "item_types": ["organic"], "limit": limite_palabras}],
        auth=auth,
        timeout=60,
    )
    if ranked.status_code != 200:
        return _vacio(host, pais, fecha, f"http_{ranked.status_code}")
    palabras, truncado, error = palabras_de(ranked.json(), fecha)
    if error:
        return _vacio(host, pais, fecha, error)
    freno = _freno(http, auth)
    if freno:
        return {
            "dominio": host,
            "pais": pais or "sin dato",
            "location_code": mercado["location_code"],
            "language_code": mercado["language_code"],
            "fecha": fecha,
            "fuente": FUENTE,
            "status": "ok",
            "razon": freno,
            "palabras": anotar_palabras(palabras, host),
            "dominios": [],
            "truncado": truncado,
        }
    competitors = http.post(
        COMPETITORS,
        json=[{**cuerpo_base, "limit": limite_dominios}],
        auth=auth,
        timeout=60,
    )
    if competitors.status_code != 200:
        return _vacio(host, pais, fecha, f"http_{competitors.status_code}")
    dominios, error = dominios_de(competitors.json(), host)
    if error:
        return _vacio(host, pais, fecha, error)
    return {
        "dominio": host,
        "pais": pais or "sin dato",
        "location_code": mercado["location_code"],
        "language_code": mercado["language_code"],
        "fecha": fecha,
        "fuente": FUENTE,
        "status": "ok",
        "palabras": anotar_palabras(palabras, host),
        "dominios": dominios,
        "truncado": truncado,
    }
