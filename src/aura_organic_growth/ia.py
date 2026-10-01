"""Prueba en vivo con IA: qué responden ChatGPT y Gemini a la pregunta de un comprador.

DataForSEO LLM Scraper, en vivo. Cada pregunta cuesta unos USD 0,004. Antes de
cada llamada se mira el saldo: bajo USD 0,10 no se llama y queda «sin dato».
La pregunta sale solo del servicio y la ciudad observados; si faltan, no se
inventa una. Nada de esto promete que una IA mencione al negocio.
"""

from __future__ import annotations

import html as html_lib
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
IGNORADOS = ("chatgpt.com", "openai.com", "vertexaisearch.cloud.google.com", "maps.google.com", "google.com")
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


def ciudad_guardada(valor: str) -> str:
    """La ciudad tal como está en la ficha. Vacía si es «sin dato» o una nota de Apollo."""
    texto = str(valor or "").strip()
    if not texto or plano(texto) == SIN_DATO or "dato de apollo" in plano(texto):
        return ""
    return texto


def pregunta_de(servicios: list[str], ciudad: str, pais: str) -> str:
    """La pregunta de un comprador. Sin ciudad se usa solo el país; sin ambos, «sin dato»."""
    ciudad = ciudad_guardada(ciudad)
    pais = str(pais or "").strip()
    if plano(pais) == SIN_DATO:
        pais = ""
    servicio = next(
        (str(s).strip() for s in servicios or [] if str(s or "").strip() and plano(str(s)) != SIN_DATO),
        "",
    )
    lugar = f"{ciudad}, {pais}" if ciudad and pais else ciudad or pais
    if not servicio or not lugar:
        return SIN_DATO
    if idioma_de(pais) == "pt-BR":
        return f"Qual {servicio} você recomenda em {lugar}?"
    return f"¿Qué {servicio} me recomiendas en {lugar}?"


_TITULO = re.compile(r"<title[^>]*>(.*?)</title\s*>", re.IGNORECASE | re.DOTALL)
_H1 = re.compile(r"<h1[^>]*>(.*?)</h1\s*>", re.IGNORECASE | re.DOTALL)
_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATRIBUTO = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_SEPARADOR = re.compile(r"\s+[–—|·•-]\s+|\s*\|\s*|:\s+")
_GENERICAS = frozenset({
    "inicio", "home", "bienvenido", "bienvenidos", "bienvenida", "welcome", "pagina principal",
    "pagina de inicio", "homepage", "home page", "sitio oficial", "sitio web",
})
MAX_PALABRAS_SERVICIO = 14


def _texto_limpio(crudo: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", " ", crudo or ""))).strip()


def _meta_description(html: str) -> str:
    for etiqueta in _META.findall(html or ""):
        atributos = {k.lower(): (a or b) for k, a, b in _ATRIBUTO.findall(etiqueta)}
        if atributos.get("name", "").lower() == "description":
            return _texto_limpio(atributos.get("content", ""))
    return ""


def _frase_de_servicio(texto: str, marcas: set[str], ciudad: str = "") -> str:
    """Un segmento del texto sin la marca, tal como está escrito. Vacío si no es una frase de servicio."""
    segmentos = [
        seg for oracion in re.split(r"[.!?](?:\s|$)", texto or "") for seg in _SEPARADOR.split(oracion)
    ]
    lugar = plano(ciudad_guardada(ciudad))
    for segmento in segmentos:
        limpio = segmento.strip(" \t-–—|·•:,;.\"'«»")
        clave = plano(limpio)
        if not limpio or clave in marcas or clave in _GENERICAS:
            continue
        if any(re.search(rf"(?<![a-z0-9]){re.escape(m)}(?![a-z0-9])", clave) for m in marcas):
            continue  # la marca va mezclada con el texto: no se corta ni se reescribe
        if not 2 <= len(limpio.split()) <= MAX_PALABRAS_SERVICIO:
            continue
        if lugar and re.search(rf"(?<![a-z0-9]){re.escape(lugar)}(?![a-z0-9])", clave):
            continue  # la ciudad ya la pone la pregunta
        return limpio[0].lower() + limpio[1:]
    return ""


def servicio_de_sitio(
    html: str | None, *, empresa: str = "", dominio: str = "", ciudad: str = ""
) -> dict | None:
    """Servicio con el texto literal de la portada: title, meta description o H1, en ese orden.

    Quita el nombre de la marca. {"servicio", "campo"} o None si ninguno da una frase.
    """
    if not html:
        return None
    marcas = marcas_de(dominio, empresa)
    titulo = _TITULO.search(html)
    h1 = _H1.search(html)
    for campo, texto in (
        ("title", _texto_limpio(titulo.group(1)) if titulo else ""),
        ("meta", _meta_description(html)),
        ("h1", _texto_limpio(h1.group(1)) if h1 else ""),
    ):
        frase = _frase_de_servicio(texto, marcas, ciudad)
        if frase:
            return {"servicio": frase, "campo": campo}
    return None


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


_ENLACE_EN_TEXTO = re.compile(r"\[[^\]]*\]\([^)]*\)")
_CORTE_NOMBRE = re.compile(r"\s[–—|-]\s|\s\|\s|:")


def _nombre_limpio(crudo: str) -> str:
    nombre = re.sub(r"\([^)]*\)", "", crudo)
    nombre = _CORTE_NOMBRE.split(nombre)[0]
    return re.sub(r"^\d+[.)]\s*", "", nombre).strip(" *_.,;:\"'«»")


def _aceptable(nombre: str, vistos: set[str], pregunta: str) -> bool:
    clave = plano(nombre)
    # Una palabra que la pregunta ya trae (IELTS, Cambridge) es el tema, no un negocio recomendado.
    en_pregunta = bool(pregunta) and re.search(rf"(?<![a-z0-9]){re.escape(clave)}(?![a-z0-9])", plano(pregunta))
    return bool(
        nombre and clave not in vistos and clave not in GENERICOS and len(nombre.split()) <= 6 and not en_pregunta
        and not nombre.endswith("?") and (nombre[0].isupper() or "." in nombre)
    )


def entidades_de(entidades: list | None, pregunta: str = "") -> list[str]:
    """Negocios que la propia respuesta marca como entidad (ChatGPT: brand_entities)."""
    salida: list[str] = []
    vistos: set[str] = set()
    for item in entidades or []:
        if not isinstance(item, dict):
            continue
        nombre = _nombre_limpio(str(item.get("title") or ""))
        if _aceptable(nombre, vistos, pregunta):
            vistos.add(plano(nombre))
            salida.append(nombre)
    return salida[:TOPE_RECOMENDADOS]


def recomendados_de(markdown: str, *, pregunta: str = "") -> list[str]:
    """Negocios en negrita dentro de una lista o un título. Extracción aproximada.

    Se quitan los enlaces antes de leer la negrita (Gemini los mete dentro) y se
    descartan las etiquetas («Por qué destaca:», «**SEO**: ...»).
    """
    salida: list[str] = []
    vistos: set[str] = set()
    for linea in _ENLACE_EN_TEXTO.sub("", markdown or "").splitlines():
        inicio = re.match(r"\s*(?:([-*•])|\d+[.)]|#{1,4})\s", linea)
        if not inicio:
            continue
        viñeta = bool(inicio.group(1))  # «- **Etiqueta**: texto» es una etiqueta; «2. **Nombre**: texto» no
        for hallado in _NEGRITA.finditer(linea):
            crudo = hallado.group(1)
            if crudo.rstrip().endswith(":") or (viñeta and linea[hallado.end():].startswith(":")):
                continue
            nombre = _nombre_limpio(crudo)
            if _aceptable(nombre, vistos, pregunta):
                vistos.add(plano(nombre))
                salida.append(nombre)
        if len(salida) >= TOPE_RECOMENDADOS:
            break
    return salida[:TOPE_RECOMENDADOS]


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


def _respuesta(data: dict) -> tuple[str, list, float | None, str | None, list]:
    """Texto de la respuesta, fuentes extra, costo y error. Todo campo ausente es «sin dato»."""
    resultado, error = tarea_de(data)
    if error:
        return "", [], None, error, []
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
        return "", [], costo, "respuesta sin texto", []
    extra = resultado.get("sources") or resultado.get("references") or []
    entidades = resultado.get("brand_entities")
    return texto, extra if isinstance(extra, list) else [], costo, None, entidades if isinstance(entidades, list) else []


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
    texto, extra, costo, error, entidades = _respuesta(resp.json())
    if error:
        fila = _vacio_motor(motor, base, error)
        fila["costo_usd"] = costo
        return fila
    citadas = urls_citadas(texto, extra)
    por_entidad = entidades_de(entidades, base["pregunta"])
    recomendados = por_entidad or recomendados_de(texto, pregunta=base["pregunta"])
    return {
        "pregunta": base["pregunta"],
        "motor": motor,
        "fecha": base["fecha"],
        "pais": base["pais"],
        "idioma": base["idioma"],
        "menciona_lead": menciona(texto, dominio, empresa),
        "recomendados": recomendados,
        "recomendados_origen": "entidades de la respuesta" if por_entidad else "negrita en listas",
        "respuesta": texto[:4000],
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
    origen_servicio: str = "observados",
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
        "servicio": next((str(x) for x in servicios or [] if str(x).strip()), SIN_DATO),
        "servicio_origen": origen_servicio if servicios else SIN_DATO,
        "ciudad": ciudad_guardada(ciudad) or SIN_DATO,
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


_TEXTOS = {
    "es": {
        "y": "y",
        "prep": "a ",
        "pregunto_uno": "Le preguntamos a {motor} «{pregunta}»",
        "pregunto_varios": "Le preguntamos {motores} «{pregunta}».",
        "recomendo": "{motor} recomendó a {lista}.",
        "y_recomendo": " y recomendó a {lista}.",
        "sin_recomendados": ".",
        "no_menciono": "No mencionó a {empresa}.",
        "si_menciono": "Sí mencionó a {empresa}.",
        "ninguno": "Ninguno mencionó a {empresa}.",
        "todos": "Todos mencionaron a {empresa}.",
        "mixto": "{si} mencionó a {empresa}; {no} no.",
        "consecuencia_ausente": "Quien le pregunta a una IA por este servicio recibe a la competencia.",
        "consecuencia_sin_nombres": "Quien le pregunta a una IA por este servicio no recibe su nombre.",
        "consecuencia_presente": "Hoy la IA lo nombra al responder esta pregunta; es una foto de hoy, no una garantía.",
        "fuentes": "Para responder, {motores} se apoyó en {lista}.",
        "fuentes_varios": "Para responder, {motores} se apoyaron en {lista}.",
        "revisada_no": "Revisamos {dominio} y {empresa} no aparece en la página.",
        "revisada_si": "Revisamos {dominio} y {empresa} sí aparece en la página.",
        "consecuencia_fuentes_ausente": "La IA citó esa página al responder y en ella {empresa} no figura.",
        "consecuencia_fuentes": "Esas son las páginas que la IA citó al responder esta pregunta.",
        "fuente": "Prueba en vivo con {motores}",
    },
    "pt-BR": {
        "y": "e",
        "prep": "ao ",
        "pregunto_uno": "Perguntamos ao {motor} «{pregunta}»",
        "pregunto_varios": "Perguntamos {motores} «{pregunta}».",
        "recomendo": "O {motor} recomendou {lista}.",
        "y_recomendo": " e ele recomendou {lista}.",
        "sin_recomendados": ".",
        "no_menciono": "Não mencionou {empresa}.",
        "si_menciono": "Mencionou {empresa}.",
        "ninguno": "Nenhum mencionou {empresa}.",
        "todos": "Todos mencionaram {empresa}.",
        "mixto": "O {si} mencionou {empresa}; o {no} não.",
        "consecuencia_ausente": "Quem pergunta a uma IA por esse serviço recebe a concorrência.",
        "consecuencia_sin_nombres": "Quem pergunta a uma IA por esse serviço não recebe o seu nome.",
        "consecuencia_presente": "Hoje a IA cita a empresa ao responder essa pergunta; é uma foto de hoje, não uma garantia.",
        "fuentes": "Para responder, {motores} se apoiou em {lista}.",
        "fuentes_varios": "Para responder, {motores} se apoiaram em {lista}.",
        "revisada_no": "Revisamos {dominio} e {empresa} não aparece na página.",
        "revisada_si": "Revisamos {dominio} e {empresa} aparece na página.",
        "consecuencia_fuentes_ausente": "A IA citou essa página ao responder e nela {empresa} não consta.",
        "consecuencia_fuentes": "Essas são as páginas que a IA citou ao responder essa pergunta.",
        "fuente": "Teste ao vivo com {motores}",
    },
}


def _lista(nombres: list[str], t: dict) -> str:
    if len(nombres) == 1:
        return nombres[0]
    return f"{', '.join(nombres[:-1])} {t['y']} {nombres[-1]}"


def _unidos(nombres: list[str], t: dict, *, prep: str = "") -> str:
    """Une con «y»/«e»; prep va delante de cada nombre (es: «a ChatGPT y a Gemini»)."""
    return _lista([f"{prep}{n}" for n in nombres], t)


def hallazgos_de_ia(registro: dict | None, *, empresa: str = "") -> list[dict]:
    """Hasta dos hallazgos: lo que respondió la IA y las fuentes que citó. Solo con motor observado."""
    if not registro or registro.get("status") != "ok":
        return []
    motores = [m for m in registro.get("motores") or [] if m.get("status") == "ok" and m.get("nivel") == "observado"]
    if not motores:
        return []
    t = _TEXTOS.get(registro.get("idioma") == "pt" and "pt-BR" or "es")
    nombre = empresa or str(registro.get("empresa") or "") or str(registro.get("dominio") or "")
    pregunta = str(registro.get("pregunta") or "")
    fecha = str(registro.get("fecha") or SIN_DATO)
    pais = str(registro.get("pais") or SIN_DATO)
    # Los registros guardados antes de estos filtros se limpian aquí, sin tocar el original.
    motores = [
        {
            **m,
            "recomendados": [n for n in m["recomendados"] if _aceptable(n, set(), pregunta)],
            "fuentes_citadas": [d for d in m["fuentes_citadas"] if not _ignorado(d)],
        }
        for m in motores
    ]
    nombres_motores = [m["motor"] for m in motores]
    fuente = t["fuente"].format(motores=f" {t['y']} ".join(nombres_motores))
    hallazgos = []

    # 1. Lo que respondió la IA.
    if len(motores) == 1:
        m = motores[0]
        rec = m["recomendados"][:5]
        texto = t["pregunto_uno"].format(motor=m["motor"], pregunta=pregunta)
        texto += t["y_recomendo"].format(lista=_lista(rec, t)) if rec else t["sin_recomendados"]
        texto += " " + (t["si_menciono"] if m["menciona_lead"] else t["no_menciono"]).format(empresa=nombre)
    else:
        partes = [t["pregunto_varios"].format(motores=_unidos(nombres_motores, t, prep=t["prep"]), pregunta=pregunta)]
        for m in motores:
            if m["recomendados"]:
                partes.append(t["recomendo"].format(motor=m["motor"], lista=_lista(m["recomendados"][:5], t)))
        si = [m["motor"] for m in motores if m["menciona_lead"]]
        no = [m["motor"] for m in motores if not m["menciona_lead"]]
        if not si:
            partes.append(t["ninguno"].format(empresa=nombre))
        elif not no:
            partes.append(t["todos"].format(empresa=nombre))
        else:
            partes.append(t["mixto"].format(si=_unidos(si, t), no=_unidos(no, t), empresa=nombre))
        texto = " ".join(partes)
    algun_si = any(m["menciona_lead"] for m in motores)
    hay_rec = any(m["recomendados"] for m in motores)
    consecuencia = (
        t["consecuencia_presente"] if algun_si
        else t["consecuencia_ausente"] if hay_rec
        else t["consecuencia_sin_nombres"]
    )
    evidencia = " | ".join(
        f"{m['motor']}, {fecha}, {pais}, {m['idioma']}. "
        f"{'Mencionó' if m['menciona_lead'] else 'No mencionó'} a {nombre}. "
        f"Recomendó: {', '.join(m['recomendados']) or 'sin dato'}. "
        f"Fuentes: {', '.join(m['fuentes_citadas']) or 'sin dato'}."
        for m in motores
    )
    hallazgos.append({
        "texto": texto, "evidencia": evidencia, "fuente": fuente, "fecha": fecha,
        "nivel": "observado", "consecuencia": consecuencia, "alcance": "sitio", "tipo": "ia_prueba",
    })

    # 2. Las fuentes citadas. «No aparece» solo si se bajó la página y se buscó el lead.
    dominios: list[str] = []
    revisadas: dict[str, dict] = {}
    for m in motores:
        for d in m["fuentes_citadas"]:
            if d not in dominios:
                dominios.append(d)
        for r in m.get("listas_revisadas") or []:
            if r.get("aparece") is not None:
                revisadas.setdefault(r["url"], r)
    if dominios:
        texto = t["fuentes" if len(motores) == 1 else "fuentes_varios"].format(motores=_unidos(nombres_motores, t), lista=_unidos(dominios[:5], t))
        ausentes = [r for r in revisadas.values() if r["aparece"] is False]
        for r in revisadas.values():
            clave = "revisada_no" if r["aparece"] is False else "revisada_si"
            texto += " " + t[clave].format(dominio=r["dominio"], empresa=nombre)
        hallazgos.append({
            "texto": texto,
            "evidencia": "; ".join([f"{m['motor']}: {', '.join(m['fuentes_citadas'])}" for m in motores if m["fuentes_citadas"]]
                                   + [f"{r['url']} revisada, {'no aparece' if r['aparece'] is False else 'aparece'}" for r in revisadas.values()]),
            "fuente": fuente, "fecha": fecha, "nivel": "observado",
            "consecuencia": (
                t["consecuencia_fuentes_ausente"].format(empresa=nombre) if ausentes else t["consecuencia_fuentes"]
            ),
            "alcance": "sitio", "tipo": "ia_fuentes",
        })
    return hallazgos
