from datetime import date

from aura_organic_growth.serp import armar_consultas, encolar


def test_no_inventa_consultas_para_llenar_veinte():
    consultas = armar_consultas(["dentista"], "Bogotá")
    assert [item["consulta"] for item in consultas] == [
        "dentista en Bogotá",
        "precio dentista",
        "mejor dentista en Bogotá",
    ]
    assert len(armar_consultas(["uno"] * 40, "Lima")) == 30


def test_sin_key_queda_sin_dato(monkeypatch):
    monkeypatch.delenv("DATAFORSEO_LOGIN", raising=False)
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)
    resultado = encolar(["dentista"], ciudad="Bogotá", pais="Colombia", hoy=date(2026, 9, 29))
    assert resultado["status"] == "sin dato"
    assert resultado["enviadas"] == []
    assert resultado["fecha"] == "2026-09-29"
    assert resultado["idioma"] == "es"
    assert resultado["dispositivo"] == "desktop"
    assert resultado["pais"] == "Colombia"


def test_cola_estandar_cuando_hay_key(monkeypatch):
    monkeypatch.setenv("DATAFORSEO_LOGIN", "login")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "clave")

    class Http:
        def post(self, url, json, auth, timeout):
            assert json[0]["priority"] == 1
            assert auth == ("login", "clave")

            class R:
                status_code = 200

                def json(self):
                    return {"cost": 0.0006, "tasks": [{"id": "t1", "cost": 0.0006}]}

            return R()

    resultado = encolar(["dentista"], ciudad="Lima", pais="Peru", session=Http(), hoy=date(2026, 9, 29))
    assert resultado["status"] == "en_cola"
    assert resultado["enviadas"][0]["task_id"] == "t1"
    assert resultado["cola"] == "estandar"
