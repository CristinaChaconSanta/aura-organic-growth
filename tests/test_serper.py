from datetime import date

from aura_organic_growth.serper import (
    AUSENTE,
    buscar,
    consultas_de,
    es_lista,
    hallazgos_de_busqueda,
    mercado_de,
)


def test_mercado_y_tope_de_diez():
    assert mercado_de("Chile") == {"gl": "cl", "hl": "es"}
    assert mercado_de("México") == {"gl": "mx", "hl": "es"}
    assert mercado_de("Brasil") == {"gl": "br", "hl": "pt"}
    assert mercado_de("Brazil")["hl"] == "pt"
    assert len(consultas_de(["uno"] * 20, "Santiago")) == 10
    assert consultas_de([], "Santiago") == []


def test_sin_key_queda_sin_dato(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)

    class Http:
        def post(self, *args, **kwargs):
            raise AssertionError("no debía llamar")

    resultado = buscar(
        ["agencia de marketing digital"],
        ciudad="Santiago",
        pais="Chile",
        dominio="dive.cl",
        session=Http(),
        hoy=date(2026, 9, 30),
    )
    assert resultado["status"] == "sin dato"
    assert resultado["razon"] == "sin SERPER_API_KEY"
    assert resultado["consultas"] == []


def test_guarda_posicion_dominios_y_lista(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "clave")
    assert es_lista("Las mejores agencias de marketing en Santiago")
    assert es_lista("Mejores empresas de software")
    assert es_lista("DIVE agencia") is False

    class R:
        def __init__(self, status, cuerpo="", texto=""):
            self.status_code = status
            self._cuerpo = cuerpo
            self.text = texto

        def json(self):
            return self._cuerpo

    class Http:
        def __init__(self):
            self.n = 0

        def post(self, url, json, headers, timeout):
            assert url == "https://google.serper.dev/search"
            assert headers["X-API-KEY"] == "clave"
            assert json["gl"] == "cl" and json["hl"] == "es"
            self.n += 1
            if self.n == 1:
                assert json["q"] == "agencia de marketing digital en Santiago"
            return R(200, {"organic": [
                {"position": 1, "title": "Otra", "link": "https://otra.cl/"},
                {
                    "position": 2,
                    "title": "Las mejores agencias de marketing en Santiago",
                    "link": "https://medio.cl/mejores-agencias",
                },
            ]})

        def get(self, url, timeout, headers):
            assert url == "https://medio.cl/mejores-agencias"
            return R(200, texto="<p>Ranking de otras agencias</p>")

    resultado = buscar(
        ["agencia de marketing digital"],
        ciudad="Santiago",
        pais="Chile",
        dominio="dive.cl",
        session=Http(),
        hoy=date(2026, 9, 30),
    )
    # armar_consultas genera tres intenciones; el mock responde igual a todas.
    consulta = resultado["consultas"][0]
    assert consulta["consulta"] == "agencia de marketing digital en Santiago"
    assert consulta["fecha"] == "2026-09-30"
    assert consulta["pais"] == "Chile"
    assert consulta["posicion"] == AUSENTE
    assert consulta["dominios"] == ["otra.cl", "medio.cl"]
    assert consulta["listas"] == [{
        "titulo": "Las mejores agencias de marketing en Santiago",
        "url": "https://medio.cl/mejores-agencias",
        "aparece": False,
    }]
    textos = [item["texto"] for item in hallazgos_de_busqueda(resultado)]
    assert "En «agencia de marketing digital en Santiago» (Chile, 2026-09-30) no aparece en el top 10." in textos
    assert any("no cita el dominio" in texto for texto in textos)
