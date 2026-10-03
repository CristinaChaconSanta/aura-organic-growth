import json
from datetime import date

import pytest

from aura_organic_growth import oferta as of

CLEMSA = """<html><head><title>Clemsa – Venta de maquinarias equipos y repuestos</title>
<meta name="description" content="Venta y arriendo de maquinaria pesada en Chile.">
<style>.x{color:red}</style></head><body>
<nav><a href="/arriendo">Arriendo</a><a href="/blog">Blog</a><a href="https://otro.cl/servicios">Afuera</a></nav>
<h1>Maquinaria pesada</h1>
<p>Ofrecemos arriendo de maquinarias de construcción modernas y confiables para tu obra.</p>
<p>Venta y arriendo de maquinaria pesada: excavadoras, grúas horquilla, cargadores y retroexcavadoras.</p>
<p>Repuestos originales y servicio técnico en San Bernardo. """ + "Texto de relleno sobre la empresa. " * 20 + """</p>
</body></html>"""
ARRIENDO = "<html><title>Arriendo</title><body><h2>Arriendo de grúas horquilla</h2><p>Grúas de 3 a 16 toneladas.</p></body></html>"


class Resp:
    def __init__(self, status_code, data=None, text=""):
        self.status_code = status_code
        self._data = data
        self.text = text

    def json(self):
        return self._data


def _gemini(cuerpo: dict) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(cuerpo, ensure_ascii=False)}]}}]}


class Http:
    def __init__(self, respuestas, paginas=None):
        self.respuestas = list(respuestas)
        self.paginas = paginas or {}
        self.posts, self.gets = [], []

    def post(self, url, json=None, headers=None, timeout=None):
        self.posts.append(url)
        return self.respuestas.pop(0)

    def get(self, url, headers=None, timeout=None):
        self.gets.append(url)
        return Resp(200, text=self.paginas[url]) if url in self.paginas else Resp(404)


BUENA = {
    "determinable": True,
    "razon": "",
    "vende": [
        {"tipo": "servicio", "que": "Arriendo de maquinaria pesada",
         "cita": "Ofrecemos arriendo de maquinarias de construcción modernas y confiables", "url": "https://clemsa.cl"},
        {"tipo": "producto", "que": "Repuestos", "cita": "repuestos que no están en la página", "url": "https://clemsa.cl"},
    ],
    "termino_comprador": "arriendo de maquinaria pesada",
    "pais_de_la_ciudad": "Chile",
    "atiende_pais": {"atiende": False, "cita": "", "url": "", "ciudad": ""},
    "preguntas": [
        "¿Qué empresas ofrecen arriendo de maquinaria pesada en San Bernardo para una obra?",
        "Necesito arriendo de maquinaria pesada en San Bernardo, ¿a quién me recomiendas?",
        "¿Clemsa hace arriendo de maquinaria pesada en San Bernardo?",
        "Arriendo de maquinaria pesada en San Bernardo",
    ],
}


@pytest.fixture(autouse=True)
def _clave(monkeypatch):
    for nombre in ["GEMINI_MODELO_OFERTA"] + [f"GEMINI_API_KEY_{n}" for n in range(2, 10)]:
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "k")


def _paginas():
    return [of.leer_pagina(CLEMSA, "https://clemsa.cl")]


def _correr(respuestas, **cambios):
    http = Http(respuestas)
    datos = {"empresa": "Clemsa", "dominio": "clemsa.cl", "ciudad": "San Bernardo", "pais": "Chile",
             "session": http, "hoy": date(2026, 10, 1), "espera": lambda s: None, **cambios}
    return of.oferta(datos.pop("paginas", _paginas()), **datos), http


def test_lee_la_pagina_sin_estilos_y_solo_enlaces_del_mismo_sitio():
    pagina = of.leer_pagina(CLEMSA, "https://clemsa.cl")
    assert "color:red" not in pagina["texto"]
    assert pagina["menu"] == ["Arriendo", "Blog"]
    assert "H1: Maquinaria pesada" in pagina["encabezados"]
    assert of.paginas_de_oferta(pagina) == ["https://clemsa.cl/arriendo"]


def test_un_estilo_sin_cerrar_por_el_corte_no_entra_como_texto():
    pagina = of.leer_pagina("<p>Paneles solares por suscripción</p><style>:root{--a:1}", "https://terra.io")
    assert pagina["texto"] == "Paneles solares por suscripción"


def test_suma_las_paginas_de_servicio_y_vuelve_a_pedir_una_portada_cortada():
    http = Http([], {"https://clemsa.cl": CLEMSA, "https://clemsa.cl/arriendo": ARRIENDO})
    paginas = of.evidencia("x" * of.CORTE_PORTADA, "https://clemsa.cl", session=http, renderizar=lambda urls: {})
    assert [p["url"] for p in paginas] == ["https://clemsa.cl", "https://clemsa.cl/arriendo"]
    assert "Grúas de 3 a 16 toneladas." in paginas[1]["texto"]


def test_sin_texto_sin_javascript_se_lee_renderizada():
    paginas = of.evidencia(
        "<html><body><div id=app></div></body></html>", "https://fresco.com", session=Http([]),
        renderizar=lambda urls: {urls[0]: {"palabras": 200, "html": CLEMSA}},
    )
    assert paginas[0]["renderizada"] is True and "arriendo de maquinarias" in paginas[0]["texto"]


def test_solo_quedan_las_citas_que_estan_en_el_sitio_y_las_preguntas_que_pasan():
    r, http = _correr([Resp(200, _gemini(BUENA))])
    assert r["status"] == "ok" and r["respaldo_termino"] == "sitio"
    assert [v["que"] for v in r["vende"]] == ["Arriendo de maquinaria pesada"]
    assert [v["que"] for v in r["citas_rechazadas"]] == ["Repuestos"]
    assert r["preguntas"] == BUENA["preguntas"][:2]
    assert [d["motivo"] for d in r["descartadas"]] == ["nombra a la empresa", "no termina en signo de pregunta"]
    assert r["fuente"] == "API de Gemini (gemini-3.5-flash)" and r["nivel"] == "inferido"
    assert len(http.posts) == 1


def test_ciudad_de_otro_pais_queda_sin_dato():
    r, _ = _correr([Resp(200, _gemini({**BUENA, "pais_de_la_ciudad": "Estados Unidos"}))], ciudad="Houston", pais="Mexico")
    assert r["status"] == "sin dato"
    assert r["razon"] == (
        "ciudad y país no coinciden: Houston queda en Estados Unidos, la ficha dice Mexico, "
        "y el sitio no muestra que atienda en Mexico"
    )


def test_sede_en_otro_pais_sigue_si_el_sitio_muestra_que_atiende_en_el_de_la_ficha():
    html = CLEMSA.replace("</body>", "<p>Também temos escritório em São Paulo para clientes no Brasil.</p></body>")
    pt = {
        **BUENA,
        "pais_de_la_ciudad": "Portugal",
        "atiende_pais": {"atiende": True, "cita": "temos escritório em São Paulo", "url": "https://clemsa.cl",
                         "ciudad": "São Paulo"},
        "preguntas": [
            "Qual empresa de arriendo de maquinaria pesada você indica em São Paulo?",
            "Qual empresa de arriendo de maquinaria pesada você indica em Lisboa?",
        ],
    }
    r, _ = _correr([Resp(200, _gemini(pt))], ciudad="Lisboa", pais="Brazil",
                   paginas=[of.leer_pagina(html, "https://clemsa.cl")])
    assert r["status"] == "ok" and r["ciudad_pregunta"] == "São Paulo"
    assert r["preguntas"] == ["Qual empresa de arriendo de maquinaria pesada você indica em São Paulo?"]
    assert r["descartadas"][0]["motivo"] == "usa Lisboa, que no queda en Brazil"
    inventada = {**pt, "atiende_pais": {**pt["atiende_pais"], "cita": "oficina en Ciudad de México"}}
    r, _ = _correr([Resp(200, _gemini(inventada))], ciudad="Lisboa", pais="Brazil",
                   paginas=[of.leer_pagina(html, "https://clemsa.cl")])
    assert r["status"] == "sin dato" and "no muestra que atienda en Brazil" in r["razon"]


def test_la_direccion_de_la_sede_extranjera_no_prueba_que_atienda_en_el_pais():
    html = CLEMSA.replace("</body>", "<p>8876 GULF FREEWAY SUITE 122 HOUSTON, TX 77022</p></body>")
    sede = {**BUENA, "pais_de_la_ciudad": "Estados Unidos",
            "atiende_pais": {"atiende": True, "cita": "8876 GULF FREEWAY SUITE 122 HOUSTON, TX 77022",
                             "url": "https://clemsa.cl", "ciudad": "Houston"}}
    r, _ = _correr([Resp(200, _gemini(sede))], ciudad="Houston", pais="Mexico",
                   paginas=[of.leer_pagina(html, "https://clemsa.cl")])
    assert r["status"] == "sin dato" and "no muestra que atienda en Mexico" in r["razon"]


def test_otra_comuna_del_mismo_pais_o_el_pais_con_otro_nombre_sigue():
    r, _ = _correr([Resp(200, _gemini({**BUENA, "pais_de_la_ciudad": "Chile"}))], ciudad="Ñuñoa")
    assert r["status"] == "ok"
    pt = {**BUENA, "pais_de_la_ciudad": "Brasil", "termino_comprador": "arriendo de maquinaria pesada",
          "preguntas": ["Qual empresa de arriendo de maquinaria pesada você indica em São Paulo?"]}
    r, _ = _correr([Resp(200, _gemini(pt))], ciudad="São Paulo", pais="Brazil")
    assert r["status"] == "ok"


def test_termino_que_no_sale_del_sitio_ni_de_las_busquedas_queda_sin_dato():
    otro = {**BUENA, "termino_comprador": "internet dedicado"}
    r, _ = _correr([Resp(200, _gemini(otro))])
    assert r["razon"] == "el término del comprador no sale del sitio ni de las búsquedas"
    r, _ = _correr([Resp(200, _gemini({**otro, "preguntas": ["¿Qué internet dedicado me recomiendas en San Bernardo?"]}))],
                   palabras_busqueda=["internet dedicado empresas"])
    assert r["status"] == "ok" and r["respaldo_termino"] == "busquedas"


def test_sin_citas_validas_o_no_determinable_no_hay_pregunta():
    r, _ = _correr([Resp(200, _gemini({**BUENA, "vende": BUENA["vende"][1:]}))])
    assert r["razon"] == "ninguna cita aparece en el sitio"
    r, _ = _correr([Resp(200, _gemini({**BUENA, "determinable": False, "razon": "solo hay estilos"}))])
    assert r["razon"] == "no determinable: solo hay estilos"


def test_saturado_reintenta_y_pasa_al_modelo_de_respaldo():
    r, http = _correr([Resp(503), Resp(503), Resp(503), Resp(200, _gemini(BUENA))])
    assert r["status"] == "ok" and r["fuente"] == "API de Gemini (gemini-3.1-flash-lite)"
    assert [u.split("/models/")[1].split(":")[0] for u in http.posts] == [
        "gemini-3.5-flash", "gemini-3.5-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]


def test_cuota_del_dia_agotada_pasa_de_inmediato_al_respaldo():
    agotada = Resp(429, text='{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}')
    r, http = _correr([agotada, Resp(200, _gemini(BUENA))])
    assert r["status"] == "ok" and len(http.posts) == 2
    r, _ = _correr([agotada, agotada])
    assert r["razon"] == "cuota diaria de Gemini agotada"


def test_sin_clave_sin_pais_o_sin_texto_no_llama(monkeypatch):
    r, http = _correr([], pais="Perú")
    assert r["razon"] == "país sin idioma definido" and not http.posts
    r, http = _correr([], paginas=[of.leer_pagina("<p>Hola</p>", "https://x.cl")])
    assert r["razon"] == "el sitio no trae texto sin JavaScript" and not http.posts
    monkeypatch.delenv("GEMINI_API_KEY")
    r, http = _correr([])
    assert r["razon"] == "sin GEMINI_API_KEY" and not http.posts


@pytest.mark.parametrize(("pregunta", "idioma", "motivo"), [
    ("Qual conta digital para menor de idade você recomenda em Brasil?", "pt-BR", "«em Brasil» en vez de «no Brasil»"),
    ("¿Qual conta digital para menor de idade no Brasil?", "pt-BR", "mezcla español"),
    ("Quais são as melhores opções de conta digital para menor de idade no Brasil?", "pt-BR", None),
    ("¿Qué conta digital para menor de idade você indica no Brasil?", "es", "mezcla portugués"),
    ("¿Qué conta digital para menor de idade hay en Mexico?", "es", "«Mexico» sin tilde"),
    ("¿Qué banco me recomiendas en Ciudad de México?", "es", "no usa el término del comprador"),
    ("¿" + "Qué conta digital para menor de idade " * 5 + "?", "es", "más de 25 palabras"),
])
def test_reglas_fijas_de_la_pregunta(pregunta, idioma, motivo):
    assert of.revisar_pregunta(
        pregunta, idioma=idioma, termino="conta digital para menor de idade", dominio="ng.cash", empresa="NG.CASH"
    ) == motivo
