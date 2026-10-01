from datetime import date

from aura_organic_growth.ia import (
    consultar,
    fuentes_citadas,
    menciona,
    pregunta_de,
    recomendados_de,
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
    assert pregunta_de(["agencia"], "", "Chile") == "sin dato"
    assert pregunta_de(["agencia"], "sin dato", "Chile") == "sin dato"


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
