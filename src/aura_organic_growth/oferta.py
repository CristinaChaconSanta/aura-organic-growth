"""Qué vende el sitio y cómo lo pide un comprador nativo de ese país.

Python junta lo que el sitio dice (title, meta, H1-H3, menú, datos
estructurados y hasta tres páginas de servicio o producto). Gemini lee eso,
separa servicios y productos con una cita literal y escribe la pregunta del
comprador en el idioma del país. Python verifica: cada cita tiene que estar en
la página, el término tiene que salir del sitio o de las búsquedas reales, y
la pregunta pasa las reglas fijas. Si algo falla, «sin dato» y no se pregunta.
"""

from __future__ import annotations

import html as html_lib
import json
import os
import re
import time
from datetime import date
from urllib.parse import urljoin, urlsplit

from aura_organic_growth.cruce import dominio_de, idioma_de, plano
from aura_organic_growth.ia import UA, ciudad_guardada, clave_gemini, marcas_de, modelos_gemini, pedir_gemini

SIN_DATO = "sin dato"
FUENTE = "API de Gemini"
# 3.5 Flash responde en la cuenta (cuota gratis: 20 por día); Flash Lite queda de respaldo si está
# saturado (503) o si se acabó la cuota del día.
MODELOS = ("gemini-3.5-flash", "gemini-3.1-flash-lite")
ESPERA_REINTENTO = 15
MAX_PAGINAS_EXTRA = 3
MAX_CARACTERES_PAGINA = 6000
MAX_PALABRAS_PREGUNTA = 25
PALABRAS_MINIMAS_TEXTO = 80
_PISTAS_OFERTA = re.compile(
    r"servicio|service|produto|producto|product|solucion|solucao|solution|catalogo|catalog|"
    r"tienda|loja|shop|planes|planos|pricing|precios|precos|arriendo|alquiler|renta|aluguel|cursos",
    re.IGNORECASE,
)
_RUIDO = re.compile(r"<(script|style|noscript|svg|template)\b.*?(?:</\1\s*>|$)", re.IGNORECASE | re.DOTALL)
MAX_CARACTERES_HTML = 2_000_000
CORTE_PORTADA = 200_000
_ETIQUETA = re.compile(r"<[^>]+>")
_TITULO = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.IGNORECASE | re.DOTALL)
_ENCABEZADO = re.compile(r"<(h[1-3])\b[^>]*>(.*?)</\1\s*>", re.IGNORECASE | re.DOTALL)
_ENLACE = re.compile(r"<a\b([^>]*)>(.*?)</a\s*>", re.IGNORECASE | re.DOTALL)
_HREF = re.compile(r"""href\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATRIBUTO = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_JSON_LD = re.compile(
    r"<script[^>]+application/ld\+json[^>]*>(.*?)</script\s*>", re.IGNORECASE | re.DOTALL
)
_CAMPOS_LD = ("@type", "name", "description", "serviceType", "category", "areaServed")
_VACIAS = frozenset({
    "de", "del", "la", "las", "el", "los", "en", "para", "por", "con", "y", "e", "o", "a", "un", "una",
    "do", "da", "dos", "das", "no", "na", "nos", "nas", "em", "com", "um", "uma", "que", "mejor",
    "melhor", "mejores", "melhores",
})
ESQUEMA = {
    "type": "OBJECT",
    "properties": {
        "determinable": {"type": "BOOLEAN"},
        "razon": {"type": "STRING"},
        "vende": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "tipo": {"type": "STRING", "enum": ["servicio", "producto"]},
                    "que": {"type": "STRING"},
                    "cita": {"type": "STRING"},
                    "url": {"type": "STRING"},
                },
                "required": ["tipo", "que", "cita", "url"],
            },
        },
        "termino_comprador": {"type": "STRING"},
        "pais_de_la_ciudad": {"type": "STRING"},
        "atiende_pais": {
            "type": "OBJECT",
            "properties": {
                "atiende": {"type": "BOOLEAN"},
                "cita": {"type": "STRING"},
                "url": {"type": "STRING"},
                "ciudad": {"type": "STRING"},
            },
            "required": ["atiende", "cita", "url", "ciudad"],
        },
        "preguntas": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": [
        "determinable", "razon", "vende", "termino_comprador", "pais_de_la_ciudad", "atiende_pais", "preguntas",
    ],
}
# Nombres con que el modelo o la ficha pueden escribir el mismo país.
PAISES = {
    "brazil": "brasil", "brasil": "brasil", "mexico": "mexico", "chile": "chile", "colombia": "colombia",
    "estados unidos": "estados unidos", "united states": "estados unidos", "eeuu": "estados unidos",
    "eua": "estados unidos", "usa": "estados unidos", "italy": "italia", "italia": "italia",
    "portugal": "portugal", "espana": "espana", "spain": "espana",
}
INSTRUCCION = """Eres un comprador nativo del país indicado. Lees lo que dice el sitio de una empresa y decides qué vende.

1. «vende»: lo que la empresa ofrece a sus clientes, separado en servicio o producto. Cada uno con «cita»: un fragmento copiado letra por letra del texto de esa URL (entre 2 y 25 palabras, sin cambiar ni una tilde), y la «url» de donde sale. No cuentes avisos de empleo, el blog ni lo que la empresa compra. Si el texto no deja claro qué vende, «determinable»: false y explica la razón.
2. «termino_comprador»: cómo nombraría lo principal que vende alguien de ese país que lo necesita y todavía no conoce la marca, tal como lo escribiría en un buscador. Palabras del comprador, no los nombres de marca ni los eslóganes del sitio. Un término en inglés se queda solo si en ese país se busca así («coworking», «growth», «software»).
3. «pais_de_la_ciudad»: el país donde queda la ciudad de la ficha, en español («Chile», «Estados Unidos»). Vacío si la ficha no trae ciudad. No mires dónde está la sede de la empresa: solo la ciudad.
4. «atiende_pais»: si el sitio muestra que la empresa vende o atiende clientes en el país indicado (una oficina, dirección, teléfono, clientes, envíos, precios o una versión del sitio para ese país), «atiende»: true, con «cita» copiada letra por letra de esa «url» y «ciudad»: la ciudad de ese país que nombra la cita, o vacío si no nombra ninguna. Sin esa evidencia, «atiende»: false.
5. «preguntas»: tres formas distintas de pedirle a una IA que te recomiende empresas o productos de ese tipo, en el idioma del país y con la naturalidad de un nativo. Cada una incluye el término del comprador y el lugar: la ciudad de la ficha si queda en el país indicado; si no, la ciudad de «atiende_pais»; si tampoco hay, el país, con su artículo («no Brasil»). Sin el nombre de la empresa. Una sola oración de máximo 25 palabras, terminada en signo de pregunta. Sin frases de marketing del sitio."""


def _texto(crudo: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(_ETIQUETA.sub(" ", crudo or ""))).strip()


def _meta_description(html: str) -> str:
    for etiqueta in _META.findall(html or ""):
        atributos = {k.lower(): (a or b) for k, a, b in _ATRIBUTO.findall(etiqueta)}
        if atributos.get("name", "").lower() == "description":
            return _texto(atributos.get("content", ""))
    return ""


def _datos_estructurados(html: str) -> list[str]:
    salida: list[str] = []

    def recorrer(nodo) -> None:
        if isinstance(nodo, list):
            for item in nodo:
                recorrer(item)
        elif isinstance(nodo, dict):
            partes = [f"{k}: {_texto(str(nodo[k]))}" for k in _CAMPOS_LD if isinstance(nodo.get(k), (str, list))]
            if partes:
                salida.append("; ".join(partes)[:300])
            for valor in nodo.values():
                if isinstance(valor, (dict, list)):
                    recorrer(valor)

    for bloque in _JSON_LD.findall(html or ""):
        try:
            recorrer(json.loads(bloque))
        except ValueError:
            continue
    return salida[:15]


def leer_pagina(html: str, url: str) -> dict:
    """Lo que la página dice, sin scripts. El texto completo sirve para verificar las citas."""
    limpio = _RUIDO.sub(" ", html or "")
    titulo = _TITULO.search(limpio)
    origen = dominio_de(url)
    enlaces: list[dict] = []
    vistos: set[str] = set()
    for atributos, cuerpo in _ENLACE.findall(limpio):
        href = _HREF.search(atributos)
        texto = _texto(cuerpo)
        if not href or not texto or len(texto.split()) > 6:
            continue
        destino = urljoin(url, href.group(1) or href.group(2)).split("#")[0]
        if dominio_de(destino) != origen or destino in vistos or not destino.startswith("http"):
            continue
        vistos.add(destino)
        enlaces.append({"texto": texto, "url": destino})
    return {
        "url": url,
        "title": _texto(titulo.group(1)) if titulo else "",
        "meta": _meta_description(limpio),
        "encabezados": [f"{n.upper()}: {_texto(t)}" for n, t in _ENCABEZADO.findall(limpio) if _texto(t)][:30],
        "menu": [e["texto"] for e in enlaces][:40],
        "datos_estructurados": _datos_estructurados(html),
        "texto": _texto(limpio),
        "enlaces": enlaces,
    }


def paginas_de_oferta(portada: dict) -> list[str]:
    """Enlaces internos que por la URL o el texto parecen servicios o productos. Hasta tres."""
    elegidas: list[str] = []
    for enlace in portada["enlaces"]:
        ruta = urlsplit(enlace["url"]).path
        if ruta in ("", "/") or enlace["url"] in elegidas:
            continue
        if _PISTAS_OFERTA.search(ruta) or _PISTAS_OFERTA.search(enlace["texto"]):
            elegidas.append(enlace["url"])
        if len(elegidas) >= MAX_PAGINAS_EXTRA:
            break
    return elegidas


def _palabras(pagina: dict) -> int:
    return len(pagina["texto"].split())


def evidencia(html: str | None, url: str, session=None, renderizar=None) -> list[dict]:
    """Portada y hasta tres páginas de servicio o producto, tal como responden hoy.

    Si la portada llegó cortada se vuelve a pedir entera; si no trae texto sin
    JavaScript, se lee renderizada.
    """
    http = session or __import__("requests")
    if url and (not html or len(html) >= CORTE_PORTADA):
        try:
            resp = http.get(url, headers=UA, timeout=20)
            if getattr(resp, "status_code", 0) == 200 and getattr(resp, "text", ""):
                html = resp.text[:MAX_CARACTERES_HTML]
        except Exception:  # noqa: BLE001
            pass
    if not html:
        return []
    portada = leer_pagina(html, url)
    if _palabras(portada) < PALABRAS_MINIMAS_TEXTO:
        if renderizar is None:
            from aura_organic_growth.render import paginas_renderizadas as renderizar
        renderizada = (renderizar([url]) or {}).get(url)
        if renderizada and renderizada.get("html"):
            portada = {**leer_pagina(renderizada["html"], url), "renderizada": True}
    paginas = [portada]
    for extra in paginas_de_oferta(portada):
        try:
            resp = http.get(extra, headers=UA, timeout=20)
        except Exception:  # noqa: BLE001
            continue
        if getattr(resp, "status_code", 0) == 200 and getattr(resp, "text", ""):
            paginas.append(leer_pagina(resp.text[:300_000], extra))
    return paginas


def _para_el_modelo(paginas: list[dict], *, empresa: str, ciudad: str, pais: str) -> str:
    bloques = [f"Empresa: {empresa or SIN_DATO}\nPaís: {pais}\nCiudad en la ficha: {ciudad or SIN_DATO}"]
    for pagina in paginas:
        bloques.append("\n".join([
            f"URL: {pagina['url']}",
            f"Title: {pagina['title']}",
            f"Meta description: {pagina['meta']}",
            "Encabezados: " + " | ".join(pagina["encabezados"]),
            "Menú: " + " | ".join(pagina["menu"]),
            "Datos estructurados: " + " | ".join(pagina["datos_estructurados"]),
            f"Texto: {pagina['texto'][:MAX_CARACTERES_PAGINA]}",
        ]))
    return "\n\n---\n\n".join(bloques)


def _pedir(http, contenido: str, espera=time.sleep) -> tuple[dict | None, str, str]:
    """JSON de la respuesta, modelo usado y razón si falló. Rota keys y modelos (ia.pedir_gemini)."""
    cuerpo = {
        "systemInstruction": {"parts": [{"text": INSTRUCCION}]},
        "contents": [{"parts": [{"text": contenido}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": ESQUEMA,
        },
    }
    data, modelo, razon = pedir_gemini(
        http, cuerpo, modelos_gemini("GEMINI_MODELO_OFERTA", MODELOS), espera=espera, pausa=ESPERA_REINTENTO
    )
    if data is None:
        return None, modelo, razon
    try:
        partes = data["candidates"][0]["content"]["parts"]
        return json.loads("".join(str(p.get("text") or "") for p in partes)), modelo, ""
    except (KeyError, IndexError, TypeError, ValueError):
        return None, modelo, "respuesta sin JSON"


def _normal(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", plano(html_lib.unescape(texto or ""))).strip()


def _pais(nombre: str) -> str:
    clave = _normal(nombre)
    return PAISES.get(clave, clave)


def _texto_completo(pagina: dict) -> str:
    return _normal(" ".join([pagina["title"], pagina["meta"], " ".join(pagina["encabezados"]), pagina["texto"]]))


def _cita_valida(item: dict, paginas: list[dict]) -> bool:
    cita = _normal(str(item.get("cita") or ""))
    if len(cita.split()) < 2:
        return False
    textos = {p["url"]: _texto_completo(p) for p in paginas}
    propia = textos.get(str(item.get("url") or ""))
    return cita in propia if propia is not None else any(cita in t for t in textos.values())


def _raices(texto: str) -> set[str]:
    return {p[:5] for p in _normal(texto).split() if len(p) >= 4 and p not in _VACIAS}


def respaldo_del_termino(termino: str, paginas: list[dict], palabras_busqueda: list[str]) -> str | None:
    """«sitio» si al menos la mitad de sus palabras están en el sitio; «búsquedas» si aparece en las del dominio."""
    raices = _raices(termino)
    if not raices:
        return None
    del_sitio = _raices(" ".join(_texto_completo(p) for p in paginas))
    if 2 * len(raices & del_sitio) >= len(raices):
        return "sitio"
    if any(raices <= _raices(p) for p in palabras_busqueda or []):
        return "busquedas"
    return None


def revisar_pregunta(pregunta: str, *, idioma: str, termino: str, dominio: str, empresa: str) -> str | None:
    """Razón por la que la pregunta no sirve, o None si pasa las reglas fijas."""
    texto = (pregunta or "").strip()
    llano = f" {_normal(texto)} "
    if not texto.endswith("?"):
        return "no termina en signo de pregunta"
    if len(texto.split()) > MAX_PALABRAS_PREGUNTA:
        return f"más de {MAX_PALABRAS_PREGUNTA} palabras"
    if any(re.search(rf"(?<![a-z0-9]){re.escape(_normal(m))}(?![a-z0-9])", llano) for m in marcas_de(dominio, empresa)):
        return "nombra a la empresa"
    if not _raices(termino) & _raices(texto):
        return "no usa el término del comprador"
    if idioma == "pt-BR":
        if texto.startswith("¿") or re.search(r" (me recomiendas|recomiendas|cual|que empresa me) ", llano):
            return "mezcla español"
        if re.search(r"\bem Brasil\b", texto):
            return "«em Brasil» en vez de «no Brasil»"
    elif idioma == "es":
        if "¿" not in texto:
            return "falta el signo de apertura"
        if re.search(r" (voce|indica para|no brasil) ", llano):
            return "mezcla portugués"
        if re.search(r"\bMexico\b", texto):
            return "«Mexico» sin tilde"
    return None


def oferta(
    paginas: list[dict],
    *,
    empresa: str,
    dominio: str,
    ciudad: str,
    pais: str,
    palabras_busqueda: list[str] | None = None,
    session=None,
    hoy: date | None = None,
    espera=time.sleep,
) -> dict:
    """Qué vende, el término del comprador y preguntas verificadas. «sin dato» con la razón si no pasa."""
    idioma = idioma_de(pais)
    ciudad = ciudad_guardada(ciudad)
    registro = {
        "fecha": (hoy or date.today()).isoformat(),
        "dominio": dominio_de(dominio),
        "pais": pais or SIN_DATO,
        "ciudad": ciudad or SIN_DATO,
        "idioma": idioma,
        "paginas_leidas": [p["url"] for p in paginas],
        "fuente": FUENTE,
        "vende": [],
        "termino": SIN_DATO,
        "respaldo_termino": None,
        "preguntas": [],
        "descartadas": [],
        "nivel": "inferido",
    }

    def sin_dato(razon: str, **extra) -> dict:
        return {**registro, **extra, "status": SIN_DATO, "razon": razon}

    if idioma == SIN_DATO:
        return sin_dato("país sin idioma definido")
    if not paginas:
        return sin_dato("la portada no respondió")
    if sum(len(p["texto"].split()) for p in paginas) < PALABRAS_MINIMAS_TEXTO:
        return sin_dato("el sitio no trae texto sin JavaScript")
    if not clave_gemini():
        return sin_dato("sin GEMINI_API_KEY")
    http = session or __import__("requests")
    respuesta, modelo, error = _pedir(
        http, _para_el_modelo(paginas, empresa=empresa, ciudad=ciudad, pais=pais), espera=espera
    )
    registro["fuente"] = f"{FUENTE} ({modelo})"
    if error or not isinstance(respuesta, dict):
        return sin_dato(error or "respuesta sin JSON")
    if not respuesta.get("determinable"):
        return sin_dato(f"no determinable: {respuesta.get('razon') or 'sin razón'}")
    vende = [v for v in respuesta.get("vende") or [] if isinstance(v, dict)]
    validos = [v for v in vende if _cita_valida(v, paginas)]
    registro["vende"] = validos
    registro["citas_rechazadas"] = [v for v in vende if v not in validos]
    if not validos:
        return sin_dato("ninguna cita aparece en el sitio")
    pais_ciudad = str(respuesta.get("pais_de_la_ciudad") or "").strip()
    registro["pais_de_la_ciudad"] = pais_ciudad or SIN_DATO
    ciudad_pregunta = ciudad
    fuera = bool(ciudad and pais_ciudad and _pais(pais_ciudad) != _pais(pais))
    if fuera:
        atiende = respuesta.get("atiende_pais") if isinstance(respuesta.get("atiende_pais"), dict) else {}
        cita = _normal(str(atiende.get("cita") or ""))
        candidata = str(atiende.get("ciudad") or "").strip()
        otra_ciudad = bool(candidata) and _normal(candidata) != _normal(ciudad) and _normal(candidata) in cita
        nombra_pais = any(
            re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", cita)
            for alias, canon in PAISES.items() if canon == _pais(pais)
        )
        # La sede extranjera (la dirección de Houston) no prueba que atienda en México.
        if not atiende.get("atiende") or not _cita_valida(atiende, paginas) or not (otra_ciudad or nombra_pais):
            return sin_dato(
                f"ciudad y país no coinciden: {ciudad} queda en {pais_ciudad}, la ficha dice {pais}, "
                f"y el sitio no muestra que atienda en {pais}"
            )
        ciudad_pregunta = candidata if otra_ciudad else ""
        registro["atiende_pais"] = {
            "cita": atiende["cita"], "url": atiende.get("url") or "", "ciudad": ciudad_pregunta or SIN_DATO,
        }
    registro["ciudad_pregunta"] = ciudad_pregunta or SIN_DATO
    termino = str(respuesta.get("termino_comprador") or "").strip()
    respaldo = respaldo_del_termino(termino, paginas, palabras_busqueda or [])
    registro.update({"termino": termino or SIN_DATO, "respaldo_termino": respaldo})
    if not respaldo:
        return sin_dato("el término del comprador no sale del sitio ni de las búsquedas")
    for pregunta in respuesta.get("preguntas") or []:
        motivo = revisar_pregunta(str(pregunta), idioma=idioma, termino=termino, dominio=dominio, empresa=empresa)
        if not motivo and fuera and re.search(rf"(?<![a-z0-9]){re.escape(_normal(ciudad))}(?![a-z0-9])", _normal(pregunta)):
            motivo = f"usa {ciudad}, que no queda en {pais}"
        destino = registro["descartadas"] if motivo else registro["preguntas"]
        destino.append({"pregunta": str(pregunta).strip(), "motivo": motivo} if motivo else str(pregunta).strip())
    if not registro["preguntas"]:
        return sin_dato("ninguna pregunta pasó las reglas")
    return {**registro, "status": "ok"}
