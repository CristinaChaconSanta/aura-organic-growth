import os

from aura_organic_growth.places_ficha import CAMPOS, LOGO_SIN_MAPA, TEXT_URL, ficha_google, para_guardar


class _Respuesta:
    status_code = 200

    def json(self):
        return {
            "places": [{
                "id": "places/abc",
                "displayName": {"text": "No guardar"},
                "rating": 4.8,
                "userRatingCount": 10,
                "formattedAddress": "Weston",
            }]
        }


class _Http:
    def __init__(self):
        self.llamadas = []

    def post(self, url, headers, json, timeout):
        self.llamadas.append((url, headers["X-Goog-FieldMask"], json["pageSize"]))
        return _Respuesta()


def test_una_busqueda_y_solo_el_place_id(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test")
    http = _Http()
    resultado = ficha_google("DIVE", "Providencia", "Chile", session=http)
    assert http.llamadas == [(TEXT_URL, CAMPOS, 1)]
    assert resultado["place_id"] == "abc"
    assert resultado["llamadas"] == 1
    guardado = para_guardar(resultado)
    assert "rating" not in guardado
    assert "address" not in resultado
    assert "Google" in LOGO_SIN_MAPA
    assert "GOOGLE_MAPS_API_KEY" in os.environ
