from datetime import date

from aura_organic_growth.ia import (
    consultar,
    fuentes_citadas,
    menciona,
    pregunta_de,
    recomendados_de,
    servicio_de_sitio,
    sin_utm,
    urls_citadas,
)

HOY = date(2026, 9, 30)
MARKDOWN = """Estas agencias suelen recomendarse en Santiago:

1. **Bigbuda** - agencia de marketing digital ([Sortlist](https://www.sortlist.com/s/marketing-digital/chile?utm_source=chatgpt.com))
2. **LaGencia**: performance y contenidos
3. **Urban Marketing** (https://clutch.co/cl/agencias?utm_source=chatgpt.com&page=2)

**Cómo elegir?** Compara casos.
"""


class Resp:
    def __init__(self, cuerpo, status=200, texto=""):
        self.cuerpo = cuerpo
        self.status_code = status
        self.text = texto

    def json(self):
        return self.cuerpo


def _ok(markdown, costo=0.004):
    return {"tasks": [{"status_code": 20000, "cost": costo, "result": [{"markdown": markdown}]}]}


def _saldo(valor):
    return {"tasks": [{"status_code": 20000, "result": [{"money": {"balance": valor}}]}]}


class Http:
    def __init__(self, saldo=0.63, respuestas=None, paginas=None):
        self.saldo = saldo
        self.respuestas = respuestas or {}
        self.paginas = paginas or {}
        self.posts = []
        self.gets = []

    def get(self, url, auth=None, timeout=None, headers=None):
        self.gets.append(url)
        if url.endswith("/appendix/user_data"):
            return Resp(_saldo(self.saldo))
        return self.paginas.get(url, Resp({}, 404))

    def post(self, url, json, auth, timeout):
        self.posts.append((url, json, auth))
        motor = "chat_gpt" if "chat_gpt" in url else "gemini"
        return self.respuestas.get(motor, Resp(_ok(MARKDOWN)))


def _credenciales(monkeypatch):
    monkeypatch.setenv("DATAFORSEO_LOGIN", "login")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "clave")


def test_pregunta_solo_con_servicio_y_ciudad_observados():
    assert pregunta_de(["agencia de marketing digital"], "Santiago", "Chile") == (
        "¿Qué agencia de marketing digital me recomiendas en Santiago, Chile?"
    )
    assert pregunta_de(["agência de marketing"], "São Paulo", "Brasil").startswith("Qual agência de marketing")
    assert pregunta_de([], "Santiago", "Chile") == "sin dato"
    assert pregunta_de(["agencia"], "", "Chile") == "¿Qué agencia me recomiendas en Chile?"
    assert pregunta_de(["agencia"], "sin dato", "Chile") == "¿Qué agencia me recomiendas en Chile?"
    assert pregunta_de(["agencia"], "Brazil (dato de Apollo)", "Brasil") == "Qual agencia você recomenda em Brasil?"
    assert pregunta_de(["agencia"], "", "") == "sin dato"


def test_sin_utm_y_dominios_citados():
    assert sin_utm("https://clutch.co/cl?utm_source=chatgpt.com&page=2") == "https://clutch.co/cl?page=2"
    citadas = urls_citadas(MARKDOWN + "https://chatgpt.com/x")
    assert [c["dominio"] for c in citadas] == ["sortlist.com", "clutch.co"]
    assert all("utm_" not in c["url"] for c in citadas)
    assert citadas[0]["titulo"] == "Sortlist"
    assert fuentes_citadas(citadas + citadas) == ["sortlist.com", "clutch.co"]


def test_recomendados_en_negrita_sin_ruido():
    assert recomendados_de(MARKDOWN) == ["Bigbuda", "LaGencia", "Urban Marketing"]


def test_menciona_por_dominio_o_marca_sin_tildes_ni_mayusculas():
    assert menciona("Recomendamos DIVE para esto", "dive.cl", "DIVE")
    assert menciona("visita https://www.dive.cl/servicios", "dive.cl")
    assert menciona("Agencia Clémsa es buena", "clemsa.cl", "Clemsa")
    assert not menciona("Hay muchas opciones diversas", "dive.cl", "DIVE")
    assert not menciona(MARKDOWN, "dive.cl", "DIVE")


def test_sin_credenciales_no_llama(monkeypatch):
    monkeypatch.delenv("DATAFORSEO_LOGIN", raising=False)
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)

    class Nada:
        def get(self, *a, **k):
            raise AssertionError("no debía llamar")

        post = get

    r = consultar(["agencia"], ciudad="Santiago", pais="Chile", dominio="dive.cl", session=Nada(), hoy=HOY)
    assert (r["status"], r["razon"]) == ("sin dato", "sin DATAFORSEO_LOGIN")
    assert r["motores"] == []


def test_servicio_literal_de_la_portada_sin_la_marca():
    clemsa = servicio_de_sitio(
        "<title>Clemsa – Venta de maquinarias equipos y repuestos</title>", empresa="Clemsa", dominio="clemsa.cl"
    )
    assert clemsa == {"servicio": "venta de maquinarias equipos y repuestos", "campo": "title"}
    meta = servicio_de_sitio(
        "<title>Inicio | Clemsa</title><meta content='Importamos maquinaria pesada. Y más.' name='description'>",
        empresa="Clemsa", dominio="clemsa.cl",
    )
    assert meta == {"servicio": "importamos maquinaria pesada", "campo": "meta"}
    h1 = servicio_de_sitio(
        "<title>English UC</title><h1> Cursos de <b>inglés</b> para adultos </h1>", empresa="English UC", dominio="uc.cl"
    )
    assert h1 == {"servicio": "cursos de inglés para adultos", "campo": "h1"}


def test_prueba_otras_oraciones_y_no_repite_la_ciudad():
    html = (
        "<title>OutLoud - Houston Event Staffing Agency</title>"
        "<meta name='description' content='Agencia Outloud Marketing. Personal para eventos y ferias.'>"
    )
    r = servicio_de_sitio(html, empresa="OutLoud Marketing", dominio="outloudmarketing.com", ciudad="Houston")
    assert r == {"servicio": "personal para eventos y ferias", "campo": "meta"}


def test_sin_frase_de_servicio_queda_sin_dato():
    assert servicio_de_sitio(None, empresa="X", dominio="x.cl") is None
    assert servicio_de_sitio("<title>Terra</title><h1>Hola</h1>", empresa="Terra", dominio="terra.io") is None
    # Marca mezclada con el texto: no se corta ni se reescribe.
    assert servicio_de_sitio("<title>Terra Energy solar</title>", empresa="Terra", dominio="terra.io") is None
    assert servicio_de_sitio("<title>Inicio</title>", empresa="Terra", dominio="terra.io") is None


def test_el_registro_dice_de_donde_salio_el_servicio(monkeypatch):
    _credenciales(monkeypatch)
    r = consultar(
        ["venta de maquinarias"], ciudad="San Bernardo", pais="Chile", dominio="clemsa.cl",
        session=Http(), hoy=HOY, origen_servicio="title", revisar_listas=False,
    )
    assert (r["servicio"], r["servicio_origen"], r["ciudad"]) == ("venta de maquinarias", "title", "San Bernardo")
    sin = consultar([], ciudad="", pais="Chile", dominio="x.cl", session=Http(), hoy=HOY, origen_servicio="sin dato")
    assert (sin["servicio_origen"], sin["status"]) == ("sin dato", "sin dato")


def test_sin_servicio_no_inventa_pregunta(monkeypatch):
    _credenciales(monkeypatch)
    r = consultar([], ciudad="Santiago", pais="Chile", dominio="dive.cl", session=Http(), hoy=HOY)
    assert r["status"] == "sin dato"
    assert r["pregunta"] == "sin dato"
    assert r["razon"] == "sin servicio o sin ciudad observados"


def test_saldo_bajo_corta_antes_de_pagar(monkeypatch):
    _credenciales(monkeypatch)
    http = Http(saldo=0.09)
    r = consultar(["agencia"], ciudad="Santiago", pais="Chile", dominio="dive.cl", session=http, hoy=HOY)
    assert http.posts == []
    assert r["status"] == "sin dato"
    assert {m["razon"] for m in r["motores"]} == {"saldo bajo USD 0.10"}
    assert all(m["nivel"] == "no determinable" and m["menciona_lead"] is None for m in r["motores"])


def test_chatgpt_y_gemini_con_el_cuerpo_y_el_registro_esperados(monkeypatch):
    _credenciales(monkeypatch)
    http = Http(respuestas={"gemini": Resp(_ok("Prueba con **DIVE** y **Otra Agencia**.", 0.004))})
    r = consultar(
        ["agencia de marketing digital"], ciudad="Santiago", pais="Chile",
        dominio="https://www.dive.cl", empresa="DIVE", session=http, hoy=HOY, revisar_listas=False,
    )
    (url1, cuerpo1, auth1), (url2, cuerpo2, _) = http.posts
    assert url1.endswith("/ai_optimization/chat_gpt/llm_scraper/live/advanced")
    assert url2.endswith("/ai_optimization/gemini/llm_scraper/live/advanced")
    assert auth1 == ("login", "clave")
    assert cuerpo1 == [{
        "keyword": "¿Qué agencia de marketing digital me recomiendas en Santiago, Chile?",
        "location_name": "Chile", "language_code": "es", "force_web_search": True,
    }]
    assert "force_web_search" not in cuerpo2[0]
    chatgpt, gemini = r["motores"]
    assert chatgpt["motor"] == "ChatGPT" and gemini["motor"] == "Gemini"
    assert chatgpt["menciona_lead"] is False
    assert chatgpt["recomendados"] == ["Bigbuda", "LaGencia", "Urban Marketing"]
    assert chatgpt["fuentes_citadas"] == ["sortlist.com", "clutch.co"]
    assert chatgpt["nivel"] == "observado" and chatgpt["costo_usd"] == 0.004
    assert (chatgpt["fecha"], chatgpt["pais"], chatgpt["idioma"]) == ("2026-09-30", "Chile", "es")
    assert gemini["menciona_lead"] is True
    assert r["status"] == "ok" and r["costo_usd"] == 0.008


def test_respuesta_sin_campos_queda_sin_dato(monkeypatch):
    _credenciales(monkeypatch)
    vacia = Resp({"tasks": [{"status_code": 20000, "result": [{}]}]})
    http = Http(respuestas={"chat_gpt": vacia, "gemini": Resp({}, 500)})
    r = consultar(["agencia"], ciudad="Santiago", pais="Chile", dominio="dive.cl", session=http, hoy=HOY)
    razones = {m["motor"]: m["razon"] for m in r["motores"]}
    assert razones == {"ChatGPT": "respuesta sin texto", "Gemini": "http_500"}
    assert r["status"] == "sin dato"
    assert all(m["menciona_lead"] is None and m["fuentes_citadas"] == [] for m in r["motores"])


def test_revisa_la_lista_citada_y_solo_afirma_con_pagina_real(monkeypatch):
    _credenciales(monkeypatch)
    relleno = "agencia digital " * 200
    paginas = {
        "https://www.sortlist.com/s/marketing-digital/chile": Resp({}, 200, f"<p>{relleno} Bigbuda</p>"),
        "https://clutch.co/cl/agencias?page=2": Resp({}, 200, "<p>corto</p>"),
    }
    http = Http(paginas=paginas, respuestas={"gemini": Resp(_ok("Sin enlaces"))})
    r = consultar(["agencia"], ciudad="Santiago", pais="Chile", dominio="dive.cl", empresa="DIVE", session=http, hoy=HOY)
    listas = {i["dominio"]: i["aparece"] for i in r["motores"][0]["listas_revisadas"]}
    assert listas == {"sortlist.com": False, "clutch.co": None}
    assert r["motores"][1]["listas_revisadas"] == []


# --- Hallazgos de la prueba con IA ---------------------------------------

from aura_organic_growth.hallazgos import cinco  # noqa: E402
from aura_organic_growth.ia import hallazgos_de_ia  # noqa: E402

PREGUNTA = "¿Qué agencia de marketing digital me recomiendas en Santiago de Chile?"


def _motor(motor, menciona, recomendados, fuentes=("sortlist.com", "clutch.co"), listas=()):
    return {
        "motor": motor, "status": "ok", "nivel": "observado", "idioma": "es",
        "menciona_lead": menciona, "recomendados": list(recomendados),
        "fuentes_citadas": list(fuentes), "listas_revisadas": list(listas),
    }


def _registro(*motores, idioma="es"):
    return {
        "status": "ok", "idioma": idioma, "empresa": "DIVE", "dominio": "dive.cl", "pregunta": PREGUNTA,
        "fecha": "2026-09-30", "pais": "Chile", "motores": list(motores),
    }


def test_hallazgo_dive_no_mencionado_nombra_a_la_competencia():
    primero, segundo = hallazgos_de_ia(_registro(_motor("ChatGPT", False, ["Bigbuda", "LaGencia", "Urban Marketing"])))
    assert primero["texto"] == (
        f"Le preguntamos a ChatGPT «{PREGUNTA}» y recomendó a Bigbuda, LaGencia y Urban Marketing. "
        "No mencionó a DIVE."
    )
    assert primero["consecuencia"] == "Quien le pregunta a una IA por este servicio recibe a la competencia."
    assert (primero["nivel"], primero["tipo"], primero["alcance"]) == ("observado", "ia_prueba", "sitio")
    assert primero["fecha"] == "2026-09-30"
    assert segundo["tipo"] == "ia_fuentes"
    assert segundo["texto"] == "Para responder, ChatGPT se apoyó en sortlist.com y clutch.co."


def test_dos_motores_en_un_solo_hallazgo():
    h = hallazgos_de_ia(_registro(_motor("ChatGPT", False, ["Bigbuda"]), _motor("Gemini", True, ["DIVE", "Otra"])))
    assert h[0]["texto"].startswith(f"Le preguntamos a ChatGPT y a Gemini «{PREGUNTA}».")
    assert h[0]["texto"].endswith("Gemini mencionó a DIVE; ChatGPT no.")
    assert "no una garantía" in h[0]["consecuencia"]


def test_ausencia_en_la_lista_solo_si_se_reviso_la_pagina():
    sin_revisar = hallazgos_de_ia(_registro(_motor("ChatGPT", False, ["A"])))[1]
    assert "no aparece" not in sin_revisar["texto"]
    revisada = {"url": "https://sortlist.com/x", "dominio": "sortlist.com", "aparece": False}
    nula = {"url": "https://clutch.co/y", "dominio": "clutch.co", "aparece": None}
    con = hallazgos_de_ia(_registro(_motor("ChatGPT", False, ["A"], listas=[revisada, nula])))[1]
    assert "Revisamos sortlist.com y DIVE no aparece en la página." in con["texto"]
    assert "clutch.co y" not in con["texto"].split("Revisamos")[1]
    assert con["consecuencia"] == "La IA citó esa página al responder y en ella DIVE no figura."


def test_sin_dato_no_genera_hallazgo_y_portugues_para_brasil():
    assert hallazgos_de_ia({"status": "sin dato", "motores": []}) == []
    assert hallazgos_de_ia(None) == []
    caido = {**_motor("ChatGPT", None, []), "status": "sin dato", "nivel": "no determinable"}
    assert hallazgos_de_ia(_registro(caido)) == []
    pt = hallazgos_de_ia(_registro(_motor("ChatGPT", False, ["A", "B"]), idioma="pt"))[0]
    assert pt["texto"].startswith("Perguntamos ao ChatGPT")
    assert pt["texto"].endswith("Não mencionou DIVE.")


def test_los_hallazgos_de_ia_van_primero_y_sin_promesas():
    ia = hallazgos_de_ia(_registro(_motor("ChatGPT", False, ["A"])))
    velocidad = {"texto": "Carga lento.", "alcance": "sitio", "tipo": "velocidad", "nivel": "observado", "consecuencia": "x"}
    error = {"texto": "Hay un error.", "alcance": "sitio", "tipo": "error", "nivel": "observado", "consecuencia": "x"}
    orden = cinco([velocidad, error, *reversed(ia)])
    assert [h["tipo"] for h in orden] == ["ia_prueba", "ia_fuentes", "velocidad", "error"]
    for h in ia:
        assert "garant" not in (h["texto"] + h["consecuencia"]).casefold()


# --- Staging: la capa de IA entra primero ---------------------------------

from aura_organic_growth.staging import hallazgos_de_medicion, juntar, parche_pendiente  # noqa: E402


def test_staging_pone_la_ia_antes_que_velocidad_sin_duplicar():
    ia = _registro(_motor("ChatGPT", False, ["Bigbuda"]))
    legibilidad = {
        "url": "https://dive.cl", "fecha": "2026-09-30", "robots": {"GPTBot": "bloqueado"},
        "llms_txt": False, "schema_tipos": [],
    }
    medicion = {
        "empresa": "DIVE", "pais": "Chile", "ia": ia, "legibilidad_ia": legibilidad,
        "hallazgos": [
            {"texto": "Carga lento.", "tipo": "velocidad", "nivel": "observado", "consecuencia": "Espera.", "fecha": "2026-09-29"},
            {"texto": "viejo", "tipo": "ia_prueba", "nivel": "observado", "consecuencia": "x"},
        ],
    }
    hallazgos = hallazgos_de_medicion(medicion, "2026-09-29")
    textos = [h["texto"] for h in hallazgos]
    assert textos[0].startswith("Le preguntamos a ChatGPT")
    assert textos[1].startswith("Para responder, ChatGPT")
    assert textos[2].startswith("El archivo que le dice a los robots")
    assert textos[3].startswith("El sitio no tiene un archivo llms.txt")
    assert textos[4] == "Carga lento."
    assert "viejo" not in textos
    assert set(hallazgos[0]) == {"texto", "evidencia", "fuente", "fecha", "nivel", "consecuencia"}
    assert parche_pendiente(hallazgos)["estado"] == "pendiente"


def test_el_refresco_lleva_la_ia_aunque_la_madurez_sea_baja():
    resumen = {"empresa": "DIVE", "pais": "Chile", "madurez": "baja", "ruta": "derivar a landing",
               "ia": _registro(_motor("ChatGPT", False, ["Bigbuda"]))}
    hallazgos = hallazgos_de_medicion(juntar(resumen, None, None), "2026-09-30")
    assert len(hallazgos) == 2 and hallazgos[0]["nivel"] == "observado"
    assert hallazgos_de_medicion({"empresa": "X", "ia": {"status": "sin dato", "motores": []}}, "2026-09-30") == []


# --- Forma real de las respuestas (verificada en vivo el 2026-09-30) -----------

from aura_organic_growth.ia import entidades_de  # noqa: E402

CHATGPT_VIVO = {"tasks": [{"status_code": 20000, "cost": 0.004, "result": [{
    "markdown": (
        "Sí. Revisé opciones.\n\n"
        "- **Bigbuda – Agencia de Marketing Digital y CRO** — Las Condes. Tiene **SEO, Google/Meta Ads**. "
        "[vitria.cl](https://vitria.cl/agencias?utm_source=chatgpt.com)\n"
        "- **Onza | Agencia de marketing digital en Santiago** — Santiago Centro.\n"
        "- **SEO y Paid Media**: servicios.\n"
    ),
    "brand_entities": [
        {"type": "chat_gpt_brand_entity", "title": "Bigbuda – Agencia de Marketing Digital y CRO", "urls": []},
        {"type": "chat_gpt_brand_entity", "title": "Onza | Agencia de marketing digital en Santiago"},
    ],
    "sources": [{"type": "chat_gpt_source", "domain": "vitria.cl", "url": "https://vitria.cl/x?utm_source=chatgpt.com", "title": "Agencias"}],
}]}]}
GEMINI_VIVO = {"tasks": [{"status_code": 20000, "cost": 0.004, "result": [{
    "markdown": (
        "Aquí tienes una selección.\n\n"
        "### 1. Para E-commerce y Analítica: **Bigbuda[presse.cl](https://presse.cl/mejores/#:~:text=2.%20Bigbuda)**\n\n"
        "* **Por qué destaca:[presse.cl](https://presse.cl/mejores/#:~:text=x)** Es referente.\n"
        "* **Ideal si:** buscas CRO.\n"
        "### 2. Para marca: **Cebra**\n"
    ),
    "sources": [{"type": "gemini_source", "domain": "presse.cl", "url": "https://presse.cl/mejores/#:~:text=2.%20Bigbuda", "title": "Presse"}],
}]}]}


def test_chatgpt_vivo_usa_las_entidades_y_gemini_la_negrita_sin_enlaces(monkeypatch):
    _credenciales(monkeypatch)
    http = Http(respuestas={"chat_gpt": Resp(CHATGPT_VIVO), "gemini": Resp(GEMINI_VIVO)})
    r = consultar(["agencia"], ciudad="Santiago", pais="Chile", dominio="dive.cl", empresa="DIVE", session=http, hoy=HOY, revisar_listas=False)
    chatgpt, gemini = r["motores"]
    assert chatgpt["recomendados"] == ["Bigbuda", "Onza"]
    assert chatgpt["recomendados_origen"] == "entidades de la respuesta"
    assert chatgpt["fuentes_citadas"] == ["vitria.cl"]
    assert gemini["recomendados"] == ["Bigbuda", "Cebra"]
    assert gemini["fuentes_citadas"] == ["presse.cl"]
    assert gemini["urls_citadas"][0]["url"] == "https://presse.cl/mejores/"
    assert gemini["respuesta"].startswith("Aquí tienes")


def test_entidades_ignoran_basura_y_duplicados():
    assert entidades_de(None) == []
    assert entidades_de([{"title": "Bigbuda – X"}, {"title": "bigbuda | Y"}, "x", {"title": ""}]) == ["Bigbuda"]


def test_filtra_palabras_de_la_pregunta_y_el_buscador_de_mapas():
    pregunta = "¿Qué cursos de IELTS y Cambridge me recomiendas en Chile?"
    gemini = _motor("Gemini", True, ["IELTS", "Cambridge", "Unity Chile"], fuentes=("maps.google.com", "unitychile.cl"))
    registro = {**_registro(gemini), "pregunta": pregunta}
    primero, segundo = hallazgos_de_ia(registro)
    assert "IELTS" not in primero["texto"].split("»", 1)[1]
    assert "recomendó a Unity Chile" in primero["texto"]
    assert "maps.google.com" not in segundo["texto"] and "unitychile.cl" in segundo["texto"]
    assert gemini["recomendados"] == ["IELTS", "Cambridge", "Unity Chile"]  # el registro guardado no se toca
    assert entidades_de([{"title": "IELTS"}, {"title": "Unity"}], pregunta) == ["Unity"]
