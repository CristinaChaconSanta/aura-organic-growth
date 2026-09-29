from datetime import date

from aura_organic_growth.senales import pauta_activa, subdominios_nuevos, vacante, wayback

HOY = date(2026, 9, 29)


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def test_dos_digestos_son_cambio_inferido():
    class Http:
        def get(self, url, params, timeout):
            return _Resp(200, [["timestamp", "digest", "statuscode"], ["20260401", "aaa", "200"], ["20260801", "bbb", "200"]])

    resultado = wayback("yo.com", session=Http(), hoy=HOY)
    assert resultado["nivel"] == "inferido"
    assert "rediseñ" not in resultado["detalle"]


def test_crt_ignora_la_renovacion_del_apex():
    class Http:
        def get(self, url, params, timeout):
            return _Resp(200, [
                {"not_before": "2026-08-01T00:00:00", "name_value": "yo.com\nwww.yo.com"},
                {"not_before": "2026-08-02T00:00:00", "name_value": "blog.yo.com"},
                {"not_before": "2025-01-01T00:00:00", "name_value": "viejo.yo.com"},
            ])

    assert subdominios_nuevos("yo.com", session=Http(), hoy=HOY)["nombres"] == ["blog.yo.com"]


def test_pauta_sin_nota_no_se_inventa():
    assert pauta_activa()["nivel"] == "no determinable"
    assert vacante("<p>Buscamos community manager</p>")["nivel"] == "no determinable"
    assert vacante("<p>Vacante de SEO</p>")["nivel"] == "observado"
