"""Qué tan legible es el sitio para los robots de IA. Solo medición.

Reglas de robots.txt para los bots de IA, llms.txt, palabras de la portada
sin JavaScript frente a las que aparecen al renderizar, y tipos JSON-LD.
llms.txt se mide y se informa; no se vende como promesa de que una IA cite.
Una ausencia solo entra desde la página renderizada: sin render, queda
«no determinable».
"""

from __future__ import annotations

import html as html_lib
import json
import re
from datetime import date
from urllib.parse import urlparse

BOTS = (
    "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot",
    "Google-Extended", "CCBot",
)
UA = {"User-Agent": "AuraOrganicGrowth/1.0 (diagnostico)"}
# Pocas palabras sin JavaScript y al renderizar aparece al menos el doble.
POCAS_SIN_JS = 150
MINIMO_EXTRA_CON_JS = 100
TIPOS_RICOS = frozenset({
    "organization", "localbusiness", "faqpage", "howto", "professionalservice", "corporation",
})
_BLOQUES = re.compile(r"<(script|style|noscript|template|svg)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_ETIQUETAS = re.compile(r"<[^>]+>")
_JSONLD = re.compile(
    r"<script\b[^>]*type\s*=\s*[\"']application/ld\+json[\"'][^>]*>(.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)


def es_html(texto: str, content_type: str = "") -> bool:
    inicio = (texto or "").lstrip()[:200].lower()
    return "html" in (content_type or "").lower() or inicio.startswith(("<!doctype", "<html", "<head", "<body"))


def reglas_robots(texto: str) -> dict[str, list[tuple[str, str]]]:
    """Reglas por agente, en minúsculas."""
    grupos: dict[str, list[tuple[str, str]]] = {}
    agentes: list[str] = []
    reglas_vistas = False
    for linea in (texto or "").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if ":" not in linea:
            continue
        clave, _, valor = linea.partition(":")
        clave, valor = clave.strip().lower(), valor.strip()
        if clave == "user-agent":
            if reglas_vistas:
                agentes, reglas_vistas = [], False
            agentes.append(valor.lower())
            grupos.setdefault(valor.lower(), [])
        elif clave in ("allow", "disallow") and agentes:
            reglas_vistas = True
            for agente in agentes:
                grupos[agente].append((clave, valor))
    return grupos


def estado_robots(texto: str) -> dict[str, str]:
    """«bloqueado» solo si el grupo aplicable cierra toda la raíz."""
    grupos = reglas_robots(texto)
    salida = {}
    for bot in BOTS:
        reglas = grupos.get(bot.lower())
        if reglas is None:
            reglas = grupos.get("*", [])
        cierra = any(k == "disallow" and v == "/" for k, v in reglas)
        abre = any(k == "allow" and v == "/" for k, v in reglas)
        salida[bot] = "bloqueado" if cierra and not abre else "permitido"
    return salida


def palabras_sin_js(html: str) -> int:
    limpio = _ETIQUETAS.sub(" ", _BLOQUES.sub(" ", html or ""))
    return len(re.findall(r"\w+", html_lib.unescape(limpio)))


def _tipos_de(nodo, salida: list[str]) -> None:
    if isinstance(nodo, list):
        for item in nodo:
            _tipos_de(item, salida)
    elif isinstance(nodo, dict):
        tipo = nodo.get("@type")
        for t in tipo if isinstance(tipo, list) else [tipo]:
            if isinstance(t, str) and t.strip() and t.strip() not in salida:
                salida.append(t.strip())
        for valor in nodo.values():
            if isinstance(valor, (dict, list)):
                _tipos_de(valor, salida)


def tipos_jsonld(html: str) -> list[str]:
    salida: list[str] = []
    for bloque in _JSONLD.findall(html or ""):
        try:
            _tipos_de(json.loads(bloque.strip()), salida)
        except ValueError:
            continue
    return salida


def tiene_schema_rico(html: str) -> list[str]:
    return [t for t in tipos_jsonld(html) if t.casefold() in TIPOS_RICOS]


def _origen(url: str) -> str:
    texto = url if "://" in url else f"https://{url}"
    partes = urlparse(texto)
    return f"{partes.scheme}://{partes.netloc}" if partes.netloc else ""


def _get(http, url: str):
    try:
        return http.get(url, headers=UA, timeout=20, allow_redirects=True)
    except Exception:  # noqa: BLE001
        return None


def leer_robots(http, origen: str) -> tuple[dict[str, str] | None, str]:
    resp = _get(http, f"{origen}/robots.txt")
    if resp is None:
        return None, "no determinable"
    estado = getattr(resp, "status_code", 0)
    if estado in (404, 410):
        return {bot: "permitido" for bot in BOTS}, "sin robots.txt"
    texto = str(getattr(resp, "text", "") or "")
    tipo = (getattr(resp, "headers", None) or {}).get("content-type", "")
    if estado != 200 or es_html(texto, tipo):
        return None, "no determinable"
    return estado_robots(texto), "leido"


def leer_llms_txt(http, origen: str) -> bool | None:
    """True si responde 200 y no es una página HTML. None si no se pudo comprobar."""
    resp = _get(http, f"{origen}/llms.txt")
    if resp is None:
        return None
    estado = getattr(resp, "status_code", 0)
    if estado in (404, 410):
        return False
    if estado != 200:
        return None
    texto = str(getattr(resp, "text", "") or "")
    tipo = (getattr(resp, "headers", None) or {}).get("content-type", "")
    return bool(texto.strip()) and not es_html(texto, tipo)


def aparece_solo_con_js(sin_js: int | None, con_js: int | None) -> bool | None:
    if sin_js is None or con_js is None:
        return None
    return sin_js < POCAS_SIN_JS and con_js >= 2 * max(sin_js, 1) and con_js - sin_js >= MINIMO_EXTRA_CON_JS


def medir(
    url: str,
    *,
    html: str | None = None,
    session=None,
    renderizador=None,
    hoy: date | None = None,
) -> dict:
    """renderizador(urls) -> {url: {"palabras": int, "html": str} | None}. Sin él, usa Chrome."""
    fecha = (hoy or date.today()).isoformat()
    origen = _origen(url)
    base = {
        "url": origen or "sin dato",
        "fecha": fecha,
        "robots": {},
        "robots_estado": "no determinable",
        "llms_txt": None,
        "palabras_sin_js": None,
        "palabras_con_js": None,
        "aparece_solo_con_js": None,
        "schema_tipos": [],
        "schema_solo_con_js": [],
        "render": "no determinable",
    }
    if not origen:
        return base
    http = session or __import__("requests")
    robots, estado = leer_robots(http, origen)
    base.update({"robots": robots or {}, "robots_estado": estado, "llms_txt": leer_llms_txt(http, origen)})
    if html is None:
        resp = _get(http, origen)
        if resp is not None and getattr(resp, "status_code", 0) == 200:
            html = str(getattr(resp, "text", "") or "")[:500_000]
    crudo = tipos_jsonld(html) if html is not None else []
    if html is not None:
        base["palabras_sin_js"] = palabras_sin_js(html)
        base["schema_tipos"] = crudo
    if renderizador is None:
        from aura_organic_growth.render import paginas_renderizadas as renderizador
    try:
        renderizada = (renderizador([origen]) or {}).get(origen)
    except Exception:  # noqa: BLE001
        renderizada = None
    if renderizada:
        base["render"] = "ok"
        base["palabras_con_js"] = renderizada.get("palabras")
        tipos_render = tipos_jsonld(str(renderizada.get("html") or ""))
        base["schema_solo_con_js"] = [t for t in tipos_render if t not in crudo]
        base["schema_tipos"] = crudo + base["schema_solo_con_js"]
    base["aparece_solo_con_js"] = aparece_solo_con_js(base["palabras_sin_js"], base["palabras_con_js"])
    return base


ASISTENTES = {
    "GPTBot": "ChatGPT", "OAI-SearchBot": "ChatGPT", "ChatGPT-User": "ChatGPT",
    "ClaudeBot": "Claude", "PerplexityBot": "Perplexity",
    "Google-Extended": "Gemini", "CCBot": "Common Crawl",
}
_PT = {
    "js": (
        "A página inicial mostra {sin} palavras a quem não executa JavaScript; com JavaScript aparecem {con}. "
        "Esse conteúdo aparece só com JavaScript."
    ),
    "js_c": "Os robôs de IA que não executam JavaScript leem uma página quase vazia.",
    "robots": "O arquivo que diz aos robôs o que podem ler bloqueia {lista}.",
    "robots_c": "Esses assistentes de IA não podem usar o site para responder.",
    "llms_si": "O site tem um arquivo llms.txt, um guia de leitura para IAs.",
    "llms_no": "O site não tem um arquivo llms.txt, um guia de leitura para IAs.",
    "llms_c": "É um sinal de ordem do site; não garante que nenhuma IA o cite.",
    "schema": "As páginas declaram dados estruturados do tipo {tipos}.",
    "schema_c": "Dão às IAs e aos buscadores uma descrição legível do negócio; não garantem menção.",
    "y": "e",
}
_ES = {
    "js": (
        "La portada muestra {sin} palabras a quien no ejecuta JavaScript; con JavaScript aparecen {con}. "
        "Ese contenido aparece solo con JavaScript."
    ),
    "js_c": "Los robots de IA que no ejecutan JavaScript leen una página casi vacía.",
    "robots": "El archivo que le dice a los robots qué pueden leer bloquea a {lista}.",
    "robots_c": "Esos asistentes de IA no pueden usar el sitio para responder.",
    "llms_si": "El sitio tiene un archivo llms.txt, una guía de lectura para IAs.",
    "llms_no": "El sitio no tiene un archivo llms.txt, una guía de lectura para IAs.",
    "llms_c": "Es una señal de orden del sitio; no garantiza que ninguna IA lo cite.",
    "schema": "Las páginas declaran datos estructurados de tipo {tipos}.",
    "schema_c": "Le dan a las IAs y a los buscadores una descripción legible del negocio; no garantizan mención.",
    "y": "y",
}
FUENTE_LECTURA = "Lectura del sitio"


def _unir(nombres: list[str], y: str) -> str:
    if len(nombres) == 1:
        return nombres[0]
    return f"{', '.join(nombres[:-1])} {y} {nombres[-1]}"


def hallazgos_de_legibilidad(registro: dict | None, *, idioma: str = "es") -> list[dict]:
    """Solo lo medido. Sin render no se afirma ausencia de contenido ni de datos estructurados."""
    if not registro:
        return []
    t = _PT if idioma == "pt-BR" else _ES
    fecha = str(registro.get("fecha") or "sin dato")
    base = {"fuente": FUENTE_LECTURA, "fecha": fecha, "nivel": "observado", "alcance": "sitio"}
    salida = []
    sin, con = registro.get("palabras_sin_js"), registro.get("palabras_con_js")
    if registro.get("aparece_solo_con_js") is True and sin is not None and con is not None:
        salida.append({
            **base, "tipo": "ia_js",
            "texto": t["js"].format(sin=sin, con=con),
            "evidencia": f"Palabras sin JavaScript: {sin}. Palabras con la página renderizada: {con}. {registro.get('url')}",
            "consecuencia": t["js_c"],
        })
    bloqueados = [b for b, v in (registro.get("robots") or {}).items() if v == "bloqueado"]
    if bloqueados:
        asistentes = list(dict.fromkeys(ASISTENTES.get(b, b) for b in bloqueados))
        salida.append({
            **base, "tipo": "ia_robots",
            "texto": t["robots"].format(lista=_unir(asistentes, t["y"])),
            "evidencia": f"robots.txt bloquea: {', '.join(bloqueados)}. {registro.get('url')}/robots.txt",
            "consecuencia": t["robots_c"],
        })
    llms = registro.get("llms_txt")
    if llms is not None:
        salida.append({
            **base, "tipo": "ia_llms",
            "texto": t["llms_si" if llms else "llms_no"],
            "evidencia": f"{registro.get('url')}/llms.txt: {'responde 200' if llms else 'no responde'}.",
            "consecuencia": t["llms_c"],
        })
    tipos = [t for t in registro.get("schema_tipos") or [] if t.casefold() in TIPOS_RICOS]
    if tipos:
        salida.append({
            **base, "tipo": "ia_schema",
            "texto": t["schema"].format(tipos=_unir(tipos[:5], t["y"])),
            "evidencia": f"JSON-LD: {', '.join(tipos)}. {registro.get('url')}",
            "consecuencia": t["schema_c"],
        })
    return salida
