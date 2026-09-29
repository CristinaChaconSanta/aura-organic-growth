from aura_organic_growth.crux import campo


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def test_sin_registro_no_dice_que_esta_bien(monkeypatch):
    monkeypatch.setenv("CRUX_API_KEY", "test")

    class Http:
        def post(self, url, json, timeout):
            return _Resp(404, {})

        def get(self, *args, **kwargs):
            raise AssertionError("un 404 de CrUX no debe caer a laboratorio")

    resultado = campo("https://yo.com", session=Http())
    assert resultado["lcp"] == "sin datos de campo"
    assert "bien" not in str(resultado).casefold()


def test_p75_es_dato_de_campo(monkeypatch):
    monkeypatch.setenv("CRUX_API_KEY", "test")

    class Http:
        def post(self, url, json, timeout):
            assert json["origin"] == "https://yo.com"
            return _Resp(200, {"record": {"metrics": {"largest_contentful_paint": {"percentiles": {"p75": 6800}}}}})

    resultado = campo("https://yo.com", session=Http())
    assert resultado["lcp_ms"] == 6800
    assert resultado["nivel"] == "observado"


def test_pagespeed_sin_campo_no_usa_el_laboratorio(monkeypatch):
    monkeypatch.setenv("PAGESPEED_API_KEY", "test")
    monkeypatch.delenv("CRUX_API_KEY", raising=False)

    class Http:
        def post(self, url, json, timeout):
            return _Resp(403, {})

        def get(self, url, params, timeout):
            return _Resp(200, {
                "loadingExperience": {},
                "lighthouseResult": {"categories": {"performance": {"score": 0.99}}},
            })

    resultado = campo("https://yo.com", session=Http())
    assert resultado["lcp"] == "sin datos de campo"
    assert "0.99" not in str(resultado)
