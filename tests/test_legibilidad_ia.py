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
