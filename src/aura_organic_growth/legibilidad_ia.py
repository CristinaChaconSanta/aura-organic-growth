"""Qué tan legible es el sitio para los robots de IA. Solo medición.

Reglas de robots.txt para los bots de IA, si el servidor deja pasar a esos
bots, llms.txt, palabras y campos (title, H1, meta description) de la portada
sin JavaScript frente a la página renderizada, y tipos JSON-LD.
llms.txt se mide y se informa; no se vende como promesa de que una IA cite.
Una ausencia solo entra desde la página renderizada: sin render, queda
«no determinable». El acceso de bots se prueba con su firma, no desde su IP:
es inferido, y no se intenta saltar ningún bloqueo.
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
FIRMAS_BOTS = {
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
    "OAI-SearchBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot",
    "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
}
CODIGOS_BLOQUEO = frozenset({401, 403, 429, 503})
_DESAFIO = ("<title>just a moment...", "/cdn-cgi/challenge-platform/", "attention required! | cloudflare")
_TITLE = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.IGNORECASE | re.DOTALL)
_H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1\s*>", re.IGNORECASE | re.DOTALL)
_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATRIBUTO = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
CAMPOS = ("title", "h1", "meta_description")
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


def _pedir_como(http, url: str, firma: str):
    """Código HTTP, «desafio» si es la página de verificación de Cloudflare, o None sin respuesta."""
    try:
        resp = http.get(url, headers={"User-Agent": firma}, timeout=20, allow_redirects=True)
    except Exception:  # noqa: BLE001
        return None
    estado = getattr(resp, "status_code", 0)
    muestra = str(getattr(resp, "text", "") or "")[:5000].casefold()
    return "desafio" if any(m in muestra for m in _DESAFIO) else estado


def acceso_bots(http, origen: str) -> tuple[dict[str, dict], str]:
    """Pide la portada con la firma de cada bot de IA. «bloqueado» solo si falla dos veces y la visita normal no."""
    if _pedir_como(http, origen, UA["User-Agent"]) != 200:
        return {}, "no determinable"
    salida = {}
    for bot, firma in FIRMAS_BOTS.items():
        intentos = [_pedir_como(http, origen, firma)]
        if intentos[0] != 200:
            intentos.append(_pedir_como(http, origen, firma))
        bloqueado = all(i == "desafio" or i in CODIGOS_BLOQUEO for i in intentos)
        salida[bot] = {
            "estado": "responde" if intentos[-1] == 200 else "bloqueado" if bloqueado else "no determinable",
            "respuestas": ["sin respuesta" if i is None else str(i) for i in intentos],
        }
    return salida, "leido"


def _texto(crudo: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(_ETIQUETAS.sub(" ", crudo or ""))).strip()


def campos_presentes(html: str) -> dict[str, bool]:
    titulo = _TITLE.search(html or "")
    meta = ""
    for etiqueta in _META.findall(html or ""):
        atributos = {k.lower(): (a or b) for k, a, b in _ATRIBUTO.findall(etiqueta)}
        if atributos.get("name", "").lower() == "description":
            meta = atributos.get("content", "")
            break
    return {
        "title": bool(titulo and _texto(titulo.group(1))),
        "h1": any(_texto(h) for h in _H1.findall(html or "")),
        "meta_description": bool(_texto(meta)),
    }


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
        "campos_solo_con_js": [],
        "acceso_bots": {},
        "acceso_estado": "no determinable",
        "render": "no determinable",
    }
    if not origen:
        return base
    http = session or __import__("requests")
    robots, estado = leer_robots(http, origen)
    base.update({"robots": robots or {}, "robots_estado": estado, "llms_txt": leer_llms_txt(http, origen)})
    acceso, acceso_estado = acceso_bots(http, origen)
    base.update({"acceso_bots": acceso, "acceso_estado": acceso_estado})
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
        html_render = str(renderizada.get("html") or "")
        tipos_render = tipos_jsonld(html_render)
        base["schema_solo_con_js"] = [t for t in tipos_render if t not in crudo]
        base["schema_tipos"] = crudo + base["schema_solo_con_js"]
        if html is not None and html_render:
            sin, con = campos_presentes(html), campos_presentes(html_render)
            base["campos_solo_con_js"] = [c for c in CAMPOS if con[c] and not sin[c]]
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
    "campos": "{lista} da página inicial aparece só com JavaScript.",
    "campos_varios": "{lista} da página inicial aparecem só com JavaScript.",
    "campos_c": "Os robôs de IA que não executam JavaScript não veem esse texto ao ler a página.",
    "nombres": {"title": "O título (title)", "h1": "o título principal (H1)", "meta_description": "a descrição para buscadores (meta description)"},
    "acceso": "Quando a página inicial é pedida como faz o robô de {lista}, o servidor bloqueia; pedida de forma normal, carrega.",
    "acceso_c": "Se o bloqueio também atinge os robôs reais, esses assistentes não conseguem ler o site para responder.",
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
    "campos": "{lista} de la portada aparece solo con JavaScript.",
    "campos_varios": "{lista} de la portada aparecen solo con JavaScript.",
    "campos_c": "Los robots de IA que no ejecutan JavaScript no ven ese texto al leer la portada.",
    "nombres": {"title": "El título (title)", "h1": "el título principal (H1)", "meta_description": "la descripción para buscadores (meta description)"},
    "acceso": "Cuando la portada se pide como lo hace el robot de {lista}, el servidor la bloquea; pedida de forma normal, carga.",
    "acceso_c": "Si el bloqueo también alcanza a los robots reales, esos asistentes no pueden leer el sitio para responder.",
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
    campos = [c for c in CAMPOS if c in (registro.get("campos_solo_con_js") or [])]
    if campos and registro.get("aparece_solo_con_js") is not True:
        nombres = [t["nombres"][c] for c in campos]
        nombres[0] = nombres[0][0].upper() + nombres[0][1:]
        salida.append({
            **base, "tipo": "ia_js_campos",
            "texto": t["campos" if len(campos) == 1 else "campos_varios"].format(lista=_unir(nombres, t["y"])),
            "evidencia": f"Ausentes en el HTML sin JavaScript y presentes al renderizar: {', '.join(campos)}. {registro.get('url')}",
            "consecuencia": t["campos_c"],
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
    # Si robots.txt ya lo cierra, ese hallazgo lo cubre.
    negados = {
        b: v for b, v in (registro.get("acceso_bots") or {}).items()
        if v.get("estado") == "bloqueado" and b not in bloqueados
    }
    if negados:
        asistentes = list(dict.fromkeys(ASISTENTES.get(b, b) for b in negados))
        salida.append({
            **base, "tipo": "ia_acceso", "nivel": "inferido",
            "texto": t["acceso"].format(lista=_unir(asistentes, t["y"])),
            "evidencia": "; ".join(f"{b}: {', '.join(v['respuestas'])}" for b, v in negados.items())
                         + f". Visita normal: 200. Firma del bot imitada, no su IP. {registro.get('url')}",
            "consecuencia": t["acceso_c"],
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
