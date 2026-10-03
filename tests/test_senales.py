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


# --- Última publicación del blog por RSS -------------------------------------

from aura_organic_growth.senales import feeds_declarados, ultima_publicacion  # noqa: E402

RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><pubDate>Mon, 03 Aug 2026 10:00:00 +0000</pubDate></item>
<item><pubDate>Tue, 12 May 2026 10:00:00 +0000</pubDate></item>
<item><pubDate>fecha rota</pubDate></item>
<item><pubDate>Fri, 01 Jan 2027 10:00:00 +0000</pubDate></item>
</channel></rss>"""
ATOM = "<feed xmlns='http://www.w3.org/2005/Atom'><entry><updated>2025-11-02T10:00:00Z</updated></entry></feed>"


class _Texto:
    def __init__(self, status, text=""):
        self.status_code = status
        self.text = text


class _HttpFeed:
    def __init__(self, paginas):
        self.paginas = paginas
        self.pedidas = []

    def get(self, url, headers=None, timeout=None):
        self.pedidas.append(url)
        return self.paginas.get(url, _Texto(404))


def test_feed_declarado_en_la_portada_sin_comentarios():
    html = """<link rel="alternate" type="application/rss+xml" href="/blog/feed/">
    <link rel="alternate" type="application/rss+xml" href="/comments/feed/">
    <link rel="stylesheet" href="/x.css">"""
    assert feeds_declarados(html, "https://dive.cl") == ["https://dive.cl/blog/feed/"]


def test_ultima_publicacion_ignora_fechas_futuras_y_rotas():
    http = _HttpFeed({"https://dive.cl/blog/feed/": _Texto(200, RSS)})
    html = '<link rel="alternate" type="application/rss+xml" href="/blog/feed/">'
    r = ultima_publicacion(html, "https://dive.cl", session=http, hoy=HOY)
    assert r == {"senal": "ultima publicacion", "nivel": "observado", "fecha": "2026-08-03", "url": "https://dive.cl/blog/feed/"}


def test_sin_feed_declarado_prueba_las_rutas_comunes_y_atom():
    http = _HttpFeed({"https://dive.cl/blog/rss.xml": _Texto(200, ATOM)})
    r = ultima_publicacion("<html></html>", "https://dive.cl", session=http, hoy=HOY)
    assert http.pedidas == ["https://dive.cl/feed/", "https://dive.cl/blog/rss.xml"]
    assert (r["fecha"], r["nivel"]) == ("2025-11-02", "observado")


def test_una_pagina_html_no_es_un_feed():
    http = _HttpFeed({"https://dive.cl/feed/": _Texto(200, "<html><body>2026-09-01</body></html>")})
    r = ultima_publicacion("", "https://dive.cl", session=http, hoy=HOY)
    assert r["nivel"] == "no determinable" and r["fecha"] is None
