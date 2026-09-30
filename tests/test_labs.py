from datetime import date

from aura_organic_growth.labs import (
    adjuntar,
    consultar,
    dominios_de,
    es_red_social,
    hallazgo_de_labs,
    leer_saldo,
    mercado_de,
    palabras_de,
)
from aura_organic_growth.staging import hallazgos_de_medicion


def _respuesta(items, total=None):
    return {
        "status_code": 20000,
        "tasks": [{
            "status_code": 20000,
            "result": [{"items": items, "total_count": total if total is not None else len(items)}],
        }],
    }


def test_mercado_segun_el_pais_guardado():
    assert mercado_de("Chile") == {"location_code": 2152, "language_code": "es"}
    assert mercado_de("México") == {"location_code": 2484, "language_code": "es"}
    assert mercado_de("Brasil")["location_code"] == 2076
    assert mercado_de("Brazil")["language_code"] == "pt"
    assert mercado_de("Peru") is None


def test_descarta_redes_y_guarda_posicion_con_trafico_estimado():
    assert es_red_social("https://www.instagram.com/dive")
    assert es_red_social("m.facebook.com")
    assert es_red_social("linkedin.com")
    assert es_red_social("youtube.com")
    assert es_red_social("www.tiktok.com")
    assert es_red_social("terraenergy.io") is False
    palabras, truncado, error = palabras_de(_respuesta([
        {
            "keyword_data": {"keyword": "dive"},
            "ranked_serp_element": {"serp_item": {"type": "organic", "rank_group": 2, "etv": 55.3}},
        },
        {
            "keyword_data": {"keyword": "trabajo arte"},
            "ranked_serp_element": {"serp_item": {"type": "organic", "rank_group": 12, "etv": None}},
        },
    ], total=2), "2026-09-30")
    assert error is None
    assert truncado is False
    assert palabras[0]["posicion"] == 2
    assert palabras[0]["trafico"] == {
        "valor": 55.3,
        "etiqueta": "estimado",
        "fuente": "DataForSEO Labs",
        "fecha": "2026-09-30",
    }
    assert "trafico" not in palabras[1]
    dominios, error_dom = dominios_de(_respuesta([
        {"domain": "instagram.com", "intersections": 40},
        {"domain": "www.linkedin.com", "intersections": 30},
        {"domain": "facebook.com", "intersections": 20},
        {"domain": "youtube.com", "intersections": 10},
        {"domain": "tiktok.com", "intersections": 8},
        {"domain": "dive.cl", "intersections": 36},
        {"domain": "otraagencia.cl", "intersections": 6},
    ]), "dive.cl")
    assert error_dom is None
    assert dominios == [{"dominio": "otraagencia.cl", "intersecciones": 6}]


def test_sin_credenciales_no_llama(monkeypatch):
    monkeypatch.delenv("DATAFORSEO_LOGIN", raising=False)
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)

    class Http:
        def post(self, *args, **kwargs):
            raise AssertionError("no debía llamar")

    resultado = consultar("dive.cl", "Chile", session=Http(), hoy=date(2026, 9, 30))
    assert resultado["status"] == "sin dato"
    assert resultado["palabras"] == []
    assert resultado["razon"] == "sin DATAFORSEO_LOGIN"


def test_consulta_chile_en_los_dos_endpoints(monkeypatch):
    monkeypatch.setenv("DATAFORSEO_LOGIN", "login")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "clave")
    llamadas = []

    class R:
        status_code = 200

        def __init__(self, cuerpo):
            self.cuerpo = cuerpo

        def json(self):
            return self.cuerpo

    class Http:
        def get(self, url, auth, timeout):
            assert url.endswith("/appendix/user_data")
            assert auth == ("login", "clave")

            class Saldo:
                status_code = 200

                def json(self):
                    return {"tasks": [{"status_code": 20000, "result": [{"money": {"balance": 1}}]}]}

            return Saldo()

        def post(self, url, json, auth, timeout):
            llamadas.append((url, json, auth))
            if "ranked_keywords" in url:
                return R(_respuesta([{
                    "keyword_data": {"keyword": "dive"},
                    "ranked_serp_element": {"serp_item": {"type": "organic", "rank_group": 2, "etv": 1.5}},
                }]))
            return R(_respuesta([{"domain": "instagram.com", "intersections": 3}, {"domain": "agencia.cl", "intersections": 2}]))

    resultado = consultar("https://www.dive.cl", "Chile", session=Http(), hoy=date(2026, 9, 30))
    assert [url.rsplit("/", 2)[-2] for url, _, _ in llamadas] == ["ranked_keywords", "competitors_domain"]
    assert llamadas[0][1][0]["location_code"] == 2152
    assert llamadas[0][1][0]["language_code"] == "es"
    assert llamadas[0][1][0]["target"] == "dive.cl"
    assert llamadas[0][2] == ("login", "clave")
    assert resultado["status"] == "ok"
    assert resultado["palabras"][0]["palabra"] == "dive"
    assert resultado["dominios"] == [{"dominio": "agencia.cl", "intersecciones": 2}]


def test_saldo_bajo_no_llama_a_labs(monkeypatch):
    monkeypatch.setenv("DATAFORSEO_LOGIN", "login")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "clave")
    assert leer_saldo({"tasks": [{"result": [{"money": {"balance": 0.09}}]}]}) == 0.09

    class Http:
        def get(self, url, auth, timeout):
            class Saldo:
                status_code = 200

                def json(self):
                    return {"tasks": [{"result": [{"money": {"balance": 0.09}}]}]}

            return Saldo()

        def post(self, *args, **kwargs):
            raise AssertionError("no debía gastar Labs")

    resultado = consultar("dive.cl", "Chile", session=Http(), hoy=date(2026, 9, 30))
    assert resultado["status"] == "sin dato"
    assert resultado["razon"] == "saldo bajo USD 0.10"
    assert resultado["palabras"] == []


def _dive():
    return {
        "status": "ok",
        "dominio": "dive.cl",
        "fecha": "2026-09-30",
        "fuente": "DataForSEO Labs",
        "truncado": False,
        "palabras": [
            {"palabra": "dive", "posicion": 2},
            {"palabra": "trabajo arte", "posicion": 12},
            {"palabra": "director de arte", "posicion": 2},
            {"palabra": "cpm", "posicion": 10},
        ],
    }


def test_dive_entra_con_empleo_y_marca_no_con_servicio():
    hallazgo = hallazgo_de_labs(_dive())
    assert hallazgo["nivel"] == "inferido"
    assert hallazgo["fuente"] == "DataForSEO Labs"
    assert hallazgo["fecha"] == "2026-09-30"
    assert "empleo" in hallazgo["texto"]
    assert "marca" in hallazgo["texto"]
    assert "no por servicios de agencia" in hallazgo["texto"]
    assert "«dive» (posición 2)" in hallazgo["texto"]
    assert "«trabajo arte» (posición 12)" in hallazgo["texto"]
    assert "estimado" not in hallazgo["texto"].casefold()
    assert hallazgo_de_labs({
        **_dive(),
        "palabras": _dive()["palabras"] + [{"palabra": "agencia de marketing", "posicion": 4}],
    }) is None
    assert hallazgos_de_medicion({"labs": _dive(), "hallazgos": []}, "2026-09-30")[0]["texto"].startswith(
        "Aparece por empleo y por la marca"
    )


def test_labs_se_pega_por_dominio_no_por_nombre():
    mediciones = adjuntar(
        {"terraenergy.io": {"empresa": "Terra"}},
        [{"dominio": "https://www.terraenergy.io", "status": "ok", "palabras": [{"palabra": "terra energy", "posicion": 3}]}],
    )
    assert mediciones["terraenergy.io"]["labs"]["palabras"][0]["palabra"] == "terra energy"
    solo_terralink = adjuntar({}, [{"dominio": "terralink.com", "palabras": [{"palabra": "terra", "posicion": 1}]}])
    assert "terraenergy.io" not in solo_terralink
    assert solo_terralink["terralink.com"]["labs"]["dominio"] == "terralink.com"
