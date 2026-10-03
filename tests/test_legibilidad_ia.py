from datetime import date

from aura_organic_growth.legibilidad_ia import (
    BOTS,
    aparece_solo_con_js,
    estado_robots,
    es_html,
    leer_llms_txt,
    leer_robots,
    medir,
    palabras_sin_js,
    tiene_schema_rico,
    tipos_jsonld,
)

HOY = date(2026, 9, 30)
ROBOTS = """
User-agent: *
Disallow: /admin

User-agent: GPTBot
User-agent: CCBot
Disallow: /

User-agent: ClaudeBot
Disallow: /privado
Allow: /
"""
HOME_VACIA = "<html><body><div id='root'></div><script>var x='muchas palabras de codigo';</script></body></html>"
JSONLD = """<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
{"@type":"Organization","name":"Terra"},{"@type":["LocalBusiness","Store"]},{"@type":"FAQPage"}]}</script>
<script type="application/ld+json">{ roto </script>"""


class Resp:
    def __init__(self, status=200, text="", content_type="text/plain"):
        self.status_code = status
        self.text = text
        self.headers = {"content-type": content_type}


class Http:
    def __init__(self, paginas):
        self.paginas = paginas
        self.pedidas = []

    def get(self, url, headers=None, timeout=None, allow_redirects=True):
        self.pedidas.append(url)
        return self.paginas.get(url, Resp(404))


def test_robots_bloquea_solo_si_cierra_la_raiz():
    estado = estado_robots(ROBOTS)
    assert estado["GPTBot"] == "bloqueado" and estado["CCBot"] == "bloqueado"
    assert estado["ClaudeBot"] == "permitido"
    assert estado["PerplexityBot"] == "permitido"
    assert set(estado) == set(BOTS)
    assert estado_robots("User-agent: *\nDisallow: /")["Google-Extended"] == "bloqueado"
    assert estado_robots("")["OAI-SearchBot"] == "permitido"


def test_robots_ausente_es_permitido_y_html_no_es_robots():
    estado, detalle = leer_robots(Http({}), "https://x.cl")
    assert detalle == "sin robots.txt" and set(estado.values()) == {"permitido"}
    http = Http({"https://x.cl/robots.txt": Resp(200, "<html>404</html>", "text/html")})
    assert leer_robots(http, "https://x.cl") == (None, "no determinable")


def test_llms_txt_presente_ausente_y_pagina_html():
    assert leer_llms_txt(Http({"https://x.cl/llms.txt": Resp(200, "# Terra\n> guía")}), "https://x.cl") is True
    assert leer_llms_txt(Http({}), "https://x.cl") is False
    soft = Http({"https://x.cl/llms.txt": Resp(200, "<!DOCTYPE html><html>Inicio</html>", "text/html")})
    assert leer_llms_txt(soft, "https://x.cl") is False
    assert leer_llms_txt(Http({"https://x.cl/llms.txt": Resp(503)}), "https://x.cl") is None
    assert es_html("<HTML>")


def test_palabras_sin_javascript_ignoran_scripts_y_estilos():
    assert palabras_sin_js(HOME_VACIA) == 0
    assert palabras_sin_js("<style>a{}</style><h1>Hola mundo</h1><p>tres palabras &amp; más</p>") == 5


def test_jsonld_lista_tipos_y_tolera_json_roto():
    assert tipos_jsonld(JSONLD) == ["Organization", "LocalBusiness", "Store", "FAQPage"]
    assert tiene_schema_rico(JSONLD) == ["Organization", "LocalBusiness", "FAQPage"]
    assert tiene_schema_rico("<html></html>") == []


def test_aparece_solo_con_js_necesita_las_dos_medidas():
    assert aparece_solo_con_js(8, 400) is True
    assert aparece_solo_con_js(254, 300) is False
    assert aparece_solo_con_js(8, None) is None
    assert aparece_solo_con_js(None, 400) is None


def _http_sitio():
    return Http({
        "https://frescofrigo.com/robots.txt": Resp(200, "User-agent: GPTBot\nDisallow: /"),
        "https://frescofrigo.com/llms.txt": Resp(404),
    })


def test_medir_con_render_marca_contenido_solo_con_js():
    renderizador = lambda urls: {urls[0]: {"palabras": 420, "html": JSONLD}}  # noqa: E731
    r = medir("https://frescofrigo.com", html=HOME_VACIA, session=_http_sitio(), renderizador=renderizador, hoy=HOY)
    assert r["palabras_sin_js"] == 0 and r["palabras_con_js"] == 420
    assert r["aparece_solo_con_js"] is True
    assert r["llms_txt"] is False
    assert r["robots"]["GPTBot"] == "bloqueado" and r["robots_estado"] == "leido"
    assert r["schema_tipos"] == ["Organization", "LocalBusiness", "Store", "FAQPage"]
    assert r["schema_solo_con_js"] == r["schema_tipos"]
    assert r["render"] == "ok" and r["fecha"] == "2026-09-30"


def test_medir_sin_render_no_afirma_ausencia():
    def falla(urls):
        raise RuntimeError("sin chrome")

    r = medir("https://frescofrigo.com", html=HOME_VACIA, session=_http_sitio(), renderizador=falla, hoy=HOY)
    assert r["palabras_sin_js"] == 0
    assert r["palabras_con_js"] is None and r["aparece_solo_con_js"] is None
    assert r["render"] == "no determinable"


def test_medir_baja_la_portada_si_no_se_la_dan():
    http = Http({"https://x.cl": Resp(200, "<p>uno dos tres</p>" + JSONLD, "text/html")})
    r = medir("x.cl", session=http, renderizador=lambda urls: {}, hoy=HOY)
    assert r["palabras_sin_js"] == 3 and r["schema_tipos"][0] == "Organization"
    assert medir("", session=http, hoy=HOY)["url"] == "sin dato"


# --- Hallazgos de legibilidad ---------------------------------------------

from aura_organic_growth.legibilidad_ia import hallazgos_de_legibilidad  # noqa: E402


def _registro(**cambios):
    base = {
        "url": "https://frescofrigo.com", "fecha": "2026-09-30", "robots": {}, "llms_txt": None,
        "palabras_sin_js": None, "palabras_con_js": None, "aparece_solo_con_js": None, "schema_tipos": [],
    }
    return {**base, **cambios}


def test_palabras_sin_js_solo_si_se_midieron_las_dos():
    medido = hallazgos_de_legibilidad(_registro(palabras_sin_js=8, palabras_con_js=420, aparece_solo_con_js=True))
    assert medido[0]["texto"].startswith("La portada muestra 8 palabras a quien no ejecuta JavaScript")
    assert "aparece solo con JavaScript" in medido[0]["texto"]
    assert "no ejecutan JavaScript" in medido[0]["consecuencia"]
    assert hallazgos_de_legibilidad(_registro(palabras_sin_js=8)) == []
    assert hallazgos_de_legibilidad(_registro(palabras_sin_js=254, palabras_con_js=260, aparece_solo_con_js=False)) == []


def test_robots_bloqueados_se_nombran_por_asistente():
    h = hallazgos_de_legibilidad(_registro(robots={"GPTBot": "bloqueado", "OAI-SearchBot": "bloqueado", "ClaudeBot": "permitido"}))
    assert h[0]["texto"] == "El archivo que le dice a los robots qué pueden leer bloquea a ChatGPT."
    assert "GPTBot, OAI-SearchBot" in h[0]["evidencia"]
    assert hallazgos_de_legibilidad(_registro(robots={"GPTBot": "permitido"})) == []


def test_llms_txt_se_informa_sin_prometer_citas():
    for valor, esperado in ((True, "tiene un archivo llms.txt"), (False, "no tiene un archivo llms.txt")):
        (h,) = hallazgos_de_legibilidad(_registro(llms_txt=valor))
        assert esperado in h["texto"]
        assert "no garantiza" in h["consecuencia"]
    assert hallazgos_de_legibilidad(_registro(llms_txt=None)) == []


def test_datos_estructurados_solo_si_los_hay_y_sin_jerga():
    (h,) = hallazgos_de_legibilidad(_registro(schema_tipos=["Organization", "FAQPage"]))
    assert h["texto"] == "Las páginas declaran datos estructurados de tipo Organization y FAQPage."
    assert "schema" not in h["texto"].casefold()
    assert hallazgos_de_legibilidad(_registro(schema_tipos=[])) == []
    assert hallazgos_de_legibilidad(None) == []


def test_datos_estructurados_solo_nombra_los_tipos_que_describen_el_negocio():
    (h,) = hallazgos_de_legibilidad(_registro(schema_tipos=["WebPage", "ReadAction", "Organization", "ListItem", "LocalBusiness"]))
    assert h["texto"] == "Las páginas declaran datos estructurados de tipo Organization y LocalBusiness."
    assert hallazgos_de_legibilidad(_registro(schema_tipos=["WebPage", "BreadcrumbList"])) == []


# --- Acceso de bots de IA y campos que aparecen solo con JavaScript -------------

from aura_organic_growth.legibilidad_ia import FIRMAS_BOTS, acceso_bots, campos_presentes  # noqa: E402

DESAFIO = "<html><head><title>Just a moment...</title></head><body>/cdn-cgi/challenge-platform/</body></html>"


class HttpPorFirma:
    """Responde según el User-Agent: una lista de respuestas por bot, en orden."""

    def __init__(self, base, por_bot):
        self.base = base
        self.por_bot = {bot: list(r) for bot, r in por_bot.items()}

    def get(self, url, headers=None, timeout=None, allow_redirects=True):
        firma = (headers or {}).get("User-Agent", "")
        for bot, respuestas in self.por_bot.items():
            if firma == FIRMAS_BOTS[bot]:
                r = respuestas.pop(0) if len(respuestas) > 1 else respuestas[0]
                if isinstance(r, Exception):
                    raise r
                return r
        return self.base


def test_bloqueo_solo_si_el_bot_falla_dos_veces_y_la_visita_normal_no():
    http = HttpPorFirma(Resp(200, "<p>hola</p>"), {
        "GPTBot": [Resp(403), Resp(403)],
        "OAI-SearchBot": [Resp(200)],
        "ClaudeBot": [OSError("se cortó"), Resp(200)],
        "PerplexityBot": [Resp(200, DESAFIO), Resp(503, DESAFIO)],
    })
    acceso, estado = acceso_bots(http, "https://dive.cl")
    assert estado == "leido"
    assert acceso["GPTBot"] == {"estado": "bloqueado", "respuestas": ["403", "403"]}
    assert acceso["OAI-SearchBot"]["estado"] == "responde"
    assert acceso["ClaudeBot"] == {"estado": "responde", "respuestas": ["sin respuesta", "200"]}
    assert acceso["PerplexityBot"]["estado"] == "bloqueado"


def test_sin_visita_normal_no_se_afirma_bloqueo():
    http = HttpPorFirma(Resp(403), {bot: [Resp(403)] for bot in FIRMAS_BOTS})
    assert acceso_bots(http, "https://dive.cl") == ({}, "no determinable")
    caidas = HttpPorFirma(Resp(200), {bot: [OSError("x"), OSError("x")] for bot in FIRMAS_BOTS})
    acceso, _ = acceso_bots(caidas, "https://dive.cl")
    assert {v["estado"] for v in acceso.values()} == {"no determinable"}


def test_hallazgo_de_acceso_es_inferido_y_no_repite_robots():
    acceso = {
        "GPTBot": {"estado": "bloqueado", "respuestas": ["403", "403"]},
        "ClaudeBot": {"estado": "bloqueado", "respuestas": ["desafio", "desafio"]},
        "PerplexityBot": {"estado": "responde", "respuestas": ["200"]},
    }
    h = hallazgos_de_legibilidad(_registro(acceso_bots=acceso, robots={"ClaudeBot": "bloqueado"}))
    robots, negado = h
    assert robots["tipo"] == "ia_robots"
    assert negado["tipo"] == "ia_acceso" and negado["nivel"] == "inferido"
    assert negado["texto"] == (
        "Cuando la portada se pide como lo hace el robot de ChatGPT, el servidor la bloquea; pedida de forma normal, carga."
    )
    assert "GPTBot: 403, 403" in negado["evidencia"] and "no su IP" in negado["evidencia"]
    assert "ClaudeBot" not in negado["evidencia"]


def test_campos_presentes_y_solo_con_js():
    crudo = "<html><head><meta name='description' content=' '></head><body><h1> </h1></body></html>"
    render = "<title>DIVE</title><meta content='Hacemos crecer tu marca' name='description'><h1>Hola <b>marca</b></h1>"
    assert campos_presentes(crudo) == {"title": False, "h1": False, "meta_description": False}
    assert campos_presentes(render) == {"title": True, "h1": True, "meta_description": True}
    r = medir("https://dive.cl", html=crudo + "<p>" + "texto " * 200 + "</p>", session=Http({}),
              renderizador=lambda urls: {urls[0]: {"palabras": 210, "html": render}}, hoy=HOY)
    assert r["campos_solo_con_js"] == ["title", "h1", "meta_description"]
    assert r["aparece_solo_con_js"] is False


def test_hallazgo_de_campos_solo_si_la_portada_no_esta_vacia():
    (h,) = hallazgos_de_legibilidad(_registro(campos_solo_con_js=["title", "h1"], aparece_solo_con_js=False))
    assert h["texto"] == "El título (title) y el título principal (H1) de la portada aparecen solo con JavaScript."
    assert h["tipo"] == "ia_js_campos" and h["nivel"] == "observado"
    vacia = _registro(campos_solo_con_js=["title"], aparece_solo_con_js=True, palabras_sin_js=3, palabras_con_js=400)
    assert [x["tipo"] for x in hallazgos_de_legibilidad(vacia)] == ["ia_js"]
    (pt,) = hallazgos_de_legibilidad(_registro(campos_solo_con_js=["h1"]), idioma="pt-BR")
    assert pt["texto"] == "O título principal (H1) da página inicial aparece só com JavaScript."
