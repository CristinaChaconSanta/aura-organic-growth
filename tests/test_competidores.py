from aura_organic_growth.competidores import clase_dominio, comparar_velocidad, repetidos
from aura_organic_growth.places_ficha import CAMPOS, ids_por_categoria


def test_separa_directorios_marketplaces_y_medios():
    resultado = repetidos(
        [
            {"dominios": ["www.yelp.com", "clinica.com", "mercadolibre.com", "eltiempo.com", "clinica.com"]},
            {"dominios": ["clinica.com", "yelp.com", "amazon.com"]},
        ],
        dominio_propio="yo.com",
    )
    assert resultado["dominios"]["negocio"][0] == {"dominio": "clinica.com", "apariciones": 2}
    assert resultado["dominios"]["directorio"][0]["dominio"] == "yelp.com"
    assert clase_dominio("mercadolibre.com.co") == "marketplace"
    assert clase_dominio("eltiempo.com") == "medio"


def test_sin_serp_no_hay_competidores():
    assert repetidos([])["status"] == "sin dato"


def test_places_de_categoria_solo_devuelve_ids(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test")

    class Http:
        def post(self, url, headers, json, timeout):
            assert headers["X-Goog-FieldMask"] == CAMPOS
            assert json["pageSize"] == 10

            class R:
                status_code = 200

                def json(self):
                    return {"places": [{"id": "places/1", "rating": 5}, {"id": "places/2"}]}

            return R()

    resultado = ids_por_categoria("inmobiliaria", "Weston", "United States", session=Http())
    assert resultado["place_ids"] == ["1", "2"]
    assert resultado["llamadas"] == 1
    assert "rating" not in resultado


def test_sin_lcp_de_campo_no_se_dice_que_esta_bien():
    comparado = comparar_velocidad({"dominio": "yo.com", "lcp_ms": None}, [{"dominio": "otro.com", "lcp_ms": 1800}])
    assert comparado["propio"]["lcp"] == "sin datos de campo"
    assert "bien" not in str(comparado).casefold()
