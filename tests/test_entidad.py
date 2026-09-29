from aura_organic_growth.entidad import entidad


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def test_sin_key_no_afirma_nada(monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_GRAPH_API_KEY", raising=False)
    resultado = entidad("DIVE")
    assert resultado["nivel"] == "no determinable"
    assert resultado["status"] == "sin dato"


def test_coincidencia_de_nombre_es_observada(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_GRAPH_API_KEY", "test")

    class Http:
        def get(self, url, params, timeout):
            assert params["query"] == "DIVE"
            return _Resp(200, {"itemListElement": [{"result": {"name": "DIVE", "@id": "kg:/m/1"}}]})

    assert entidad("DIVE", session=Http())["nivel"] == "observado"


def test_otro_nombre_no_se_toma_como_la_marca(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_GRAPH_API_KEY", "test")

    class Http:
        def get(self, url, params, timeout):
            return _Resp(200, {"itemListElement": [{"result": {"name": "Otra cosa", "@id": "kg:/m/2"}}]})

    assert entidad("DIVE", session=Http())["nivel"] == "no determinable"
