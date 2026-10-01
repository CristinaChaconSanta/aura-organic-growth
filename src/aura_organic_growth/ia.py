"""Prueba en vivo con IA: qué responden ChatGPT y Gemini a la pregunta de un comprador.

DataForSEO LLM Scraper, en vivo. Cada pregunta cuesta unos USD 0,004. Antes de
cada llamada se mira el saldo: bajo USD 0,10 no se llama y queda «sin dato».
La pregunta sale solo del servicio y la ciudad observados; si faltan, no se
inventa una. Nada de esto promete que una IA mencione al negocio.
"""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aura_organic_growth.cruce import dominio_de, idioma_de, plano
from aura_organic_growth.labs import credenciales, freno_de_saldo, tarea_de
from aura_organic_growth.serper import es_lista

BASE = "https://api.dataforseo.com/v3/ai_optimization"
MOTORES = {
    "ChatGPT": f"{BASE}/chat_gpt/llm_scraper/live/advanced",
    "Gemini": f"{BASE}/gemini/llm_scraper/live/advanced",
}
FUENTE = "DataForSEO LLM Scraper"
SIN_DATO = "sin dato"
UA = {"User-Agent": "AuraOrganicGrowth/1.0 (diagnostico)"}
MERCADOS = {
    "chile": {"location_name": "Chile", "language_code": "es"},
    "mexico": {"location_name": "Mexico", "language_code": "es"},
    "colombia": {"location_name": "Colombia", "language_code": "es"},
    "brasil": {"location_name": "Brazil", "language_code": "pt"},
    "brazil": {"location_name": "Brazil", "language_code": "pt"},
}
DIRECTORIOS = frozenset({
    "sortlist.com", "clutch.co", "goodfirms.co", "designrush.com",
    "themanifest.com", "agencyspotter.com",
})
# Hosts que no son una fuente del tema: el propio buscador de la IA.
IGNORADOS = ("chatgpt.com", "openai.com", "vertexaisearch.cloud.google.com")
TOPE_RECOMENDADOS = 8
TOPE_LISTAS = 3
PALABRAS_MINIMAS_LISTA = 300
GENERICOS = frozenset({
    "nota", "importante", "consejo", "resumen", "conclusion", "recomendacion",
    "tip", "en resumen", "como elegir", "como elegir la mejor", "te recomiendo",
    "ojo", "atencion", "ejemplo", "bonus",
})
_URL = re.compile(r"https?://[^\s)\]>\"'<]+")
_ENLACE = re.compile(r"\[([^\]]{1,200})\]\((https?://[^)\s]+)[^)]*\)")
_NEGRITA = re.compile(r"\*\*([^*\n]{2,80})\*\*")


def mercado_de(pais: str) -> dict | None:
    return MERCADOS.get(plano(pais))


def pregunta_de(servicios: list[str], ciudad: str, pais: str) -> str:
    """La pregunta de un comprador. Solo con servicio y ciudad observados."""
    ciudad = str(ciudad or "").strip()
    pais = str(pais or "").strip()
    if not ciudad or plano(ciudad) == SIN_DATO:
        return SIN_DATO
    servicio = next(
        (str(s).strip() for s in servicios or [] if str(s or "").strip() and plano(str(s)) != SIN_DATO),
        "",
    )
    if not servicio:
        return SIN_DATO
    lugar = ciudad if not pais or plano(pais) == SIN_DATO else f"{ciudad}, {pais}"
    if idioma_de(pais) == "pt-BR":
        return f"Qual {servicio} você recomenda em {lugar}?"
    return f"¿Qué {servicio} me recomiendas en {lugar}?"


def sin_utm(url: str) -> str:
    partes = urlsplit(url.strip().rstrip(".,;"))
    consulta = [(k, v) for k, v in parse_qsl(partes.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(consulta), ""))


def _ignorado(host: str) -> bool:
    return not host or any(host == h or host.endswith("." + h) for h in IGNORADOS)


def urls_citadas(markdown: str, extra: list | None = None) -> list[dict]:
    """URL sin utm y título del enlace si lo hay. Sin repetir."""
    salida: list[dict] = []
    vistas: set[str] = set()

    def sumar(url: str, titulo: str = "") -> None:
        limpia = sin_utm(url)
        host = dominio_de(limpia)
        if _ignorado(host) or limpia in vistas:
            return
        vistas.add(limpia)
        salida.append({"url": limpia, "dominio": host, "titulo": titulo.strip()})

    for titulo, url in _ENLACE.findall(markdown or ""):
        sumar(url, titulo)
    for url in _URL.findall(markdown or ""):
        sumar(url)
    for item in extra or []:
        if isinstance(item, dict) and str(item.get("url") or "").startswith("http"):
            sumar(str(item["url"]), str(item.get("title") or ""))
    return salida


def fuentes_citadas(citadas: list[dict]) -> list[str]:
    vistos: list[str] = []
    for item in citadas:
        if item["dominio"] not in vistos:
            vistos.append(item["dominio"])
    return vistos


def recomendados_de(markdown: str, *, pregunta: str = "") -> list[str]:
    """Negocios que la respuesta destaca en negrita. Es una extracción aproximada."""
    salida: list[str] = []
    vistos: set[str] = set()
    for crudo in _NEGRITA.findall(markdown or ""):
        nombre = re.sub(r"\([^)]*\)", "", crudo)
        nombre = re.split(r"\s[–—-]\s|:", nombre)[0]
        nombre = re.sub(r"^\d+[.)]\s*", "", nombre).strip(" *_.,;:\"'«»")
        clave = plano(nombre)
        if not nombre or clave in vistos or clave in GENERICOS or len(nombre.split()) > 6:
            continue
        if nombre.endswith("?") or clave == plano(pregunta):
            continue
        if not (nombre[0].isupper() or "." in nombre):
            continue
        vistos.add(clave)
        salida.append(nombre)
        if len(salida) >= TOPE_RECOMENDADOS:
            break
    return salida


def marcas_de(dominio: str, empresa: str = "") -> set[str]:
    host = dominio_de(dominio)
    marcas = set()
    etiqueta = plano(host.split(".")[0]) if host else ""
    if len(etiqueta) >= 3:
        marcas.add(etiqueta)
    nombre = plano(empresa)
    if len(nombre) >= 3 and nombre != SIN_DATO:
        marcas.add(nombre)
    return marcas


def menciona(texto: str, dominio: str, empresa: str = "") -> bool:
    """Por dominio o por marca, sin mayúsculas ni tildes. La marca va como palabra entera."""
    cuerpo = plano(texto)
    host = dominio_de(dominio)
    if host and host in cuerpo:
        return True
    for marca in marcas_de(dominio, empresa):
        if re.search(rf"(?<![a-z0-9]){re.escape(marca)}(?![a-z0-9])", cuerpo):
            return True
    return False


def _vacio_motor(motor: str, base: dict, razon: str) -> dict:
    return {
        "pregunta": base["pregunta"],
        "motor": motor,
        "fecha": base["fecha"],
        "pais": base["pais"],
        "idioma": base["idioma"],
        "menciona_lead": None,
        "recomendados": [],
        "fuentes_citadas": [],
        "urls_citadas": [],
        "listas_revisadas": [],
        "costo_usd": None,
        "nivel": "no determinable",
        "status": "sin dato",
        "razon": razon,
    }


def _respuesta(data: dict) -> tuple[str, list, float | None, str | None]:
    """Texto de la respuesta, fuentes extra, costo y error. Todo campo ausente es «sin dato»."""
    resultado, error = tarea_de(data)
    if error:
        return "", [], None, error
    tarea = ((data or {}).get("tasks") or [{}])[0]
    costo = tarea.get("cost", (data or {}).get("cost"))
    costo = float(costo) if isinstance(costo, (int, float)) else None
    texto = resultado.get("markdown")
    if not isinstance(texto, str) or not texto.strip():
        for item in resultado.get("items") or []:
            candidato = (item or {}).get("markdown") or (item or {}).get("text")
            if isinstance(candidato, str) and candidato.strip():
                texto = candidato
                break
    if not isinstance(texto, str) or not texto.strip():
        return "", [], costo, "respuesta sin texto"
    extra = resultado.get("sources") or resultado.get("references") or []
    return texto, extra if isinstance(extra, list) else [], costo, None


def _revisar_lista(http, item: dict, dominio: str, empresa: str) -> dict:
    """Baja la página citada y mira si el lead está. Sin página con contenido, no se afirma nada."""
    fila = {"url": item["url"], "dominio": item["dominio"], "titulo": item.get("titulo") or "", "aparece": None}
    try:
        resp = http.get(item["url"], timeout=20, headers=UA)
    except Exception:  # noqa: BLE001
        return fila
    if getattr(resp, "status_code", 0) != 200:
        return fila
    texto = str(getattr(resp, "text", "") or "")[:500_000]
    if len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", texto))) < PALABRAS_MINIMAS_LISTA:
        return fila
    fila["aparece"] = menciona(texto, dominio, empresa)
    return fila


def _es_candidata(item: dict) -> bool:
    return item["dominio"] in DIRECTORIOS or es_lista(item.get("titulo") or "")


def _consultar_motor(http, auth, motor: str, base: dict, dominio: str, empresa: str) -> dict:
    freno = freno_de_saldo(http, auth)
    if freno:
        return _vacio_motor(motor, base, freno)
    cuerpo = {"keyword": base["pregunta"], **base["mercado"]}
    if motor == "ChatGPT":
        cuerpo["force_web_search"] = True
    try:
        resp = http.post(MOTORES[motor], json=[cuerpo], auth=auth, timeout=180)
    except Exception:  # noqa: BLE001
        return _vacio_motor(motor, base, "sin respuesta")
    if resp.status_code != 200:
        return _vacio_motor(motor, base, f"http_{resp.status_code}")
    texto, extra, costo, error = _respuesta(resp.json())
    if error:
        fila = _vacio_motor(motor, base, error)
        fila["costo_usd"] = costo
        return fila
    citadas = urls_citadas(texto, extra)
    return {
        "pregunta": base["pregunta"],
        "motor": motor,
        "fecha": base["fecha"],
        "pais": base["pais"],
        "idioma": base["idioma"],
        "menciona_lead": menciona(texto, dominio, empresa),
        "recomendados": recomendados_de(texto, pregunta=base["pregunta"]),
        "fuentes_citadas": fuentes_citadas(citadas),
        "urls_citadas": citadas,
        "listas_revisadas": [],
        "costo_usd": costo,
        "nivel": "observado",
        "status": "ok",
    }


def consultar(
    servicios: list[str],
    *,
    ciudad: str,
    pais: str,
    dominio: str,
    empresa: str = "",
    session=None,
    hoy: date | None = None,
    motores: tuple[str, ...] = ("ChatGPT", "Gemini"),
    revisar_listas: bool = True,
) -> dict:
    fecha = (hoy or date.today()).isoformat()
    mercado = mercado_de(pais)
    pregunta = pregunta_de(servicios, ciudad, pais)
    base = {
        "pregunta": pregunta,
        "fecha": fecha,
        "pais": pais or SIN_DATO,
        "idioma": mercado["language_code"] if mercado else SIN_DATO,
        "mercado": mercado,
    }
    registro = {
        "dominio": dominio_de(dominio),
        "empresa": empresa or SIN_DATO,
        "pregunta": pregunta,
        "fecha": fecha,
        "pais": base["pais"],
        "idioma": base["idioma"],
        "fuente": FUENTE,
        "motores": [],
        "costo_usd": None,
    }

    def sin_dato(razon: str) -> dict:
        return {**registro, "status": "sin dato", "razon": razon}

    if pregunta == SIN_DATO:
        return sin_dato("sin servicio o sin ciudad observados")
    if not mercado:
        return sin_dato("pais sin mercado de LLM Scraper")
    login, password = credenciales()
    if not login or not password:
        return sin_dato("sin DATAFORSEO_LOGIN")
    http = session or __import__("requests")
    auth = (login, password)
    filas = [_consultar_motor(http, auth, motor, base, dominio, empresa) for motor in motores]
    if revisar_listas:
        revisadas: dict[str, dict] = {}
        for fila in filas:
            for item in fila["urls_citadas"]:
                if item["url"] in revisadas or len(revisadas) >= TOPE_LISTAS or not _es_candidata(item):
                    continue
                revisadas[item["url"]] = _revisar_lista(http, item, dominio, empresa)
            fila["listas_revisadas"] = [
                revisadas[i["url"]] for i in fila["urls_citadas"] if i["url"] in revisadas
            ]
    costos = [f["costo_usd"] for f in filas if isinstance(f["costo_usd"], (int, float))]
    estado = "ok" if any(f["status"] == "ok" for f in filas) else "sin dato"
    registro.update({"motores": filas, "costo_usd": round(sum(costos), 6) if costos else None, "status": estado})
    if estado == "sin dato":
        registro["razon"] = "; ".join(sorted({str(f.get("razon")) for f in filas}))
    return registro
