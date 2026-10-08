import gzip

from aura_organic_growth.auditoria_seo import indexacion, robots
from aura_organic_growth.auditoria_seo.inventario import leer_sitemap
from aura_organic_growth.auditoria_seo.plantillas import es_paginacion, parametros, plantilla, plataforma
from aura_organic_growth.auditoria_seo.rastreo import compactar, es_interna, leer_cabeza

ROBOTS_SHOPIFY = """
User-agent: *
Allow: /
Disallow: /cart/
Disallow: /collections/*sort_by*
Disallow: /collections/*+*
Allow: /collections/*sort_by*permitido
Sitemap: https://tienda.co/sitemap.xml

User-agent: Googlebot
User-agent: Bingbot
Disallow: /privado
"""

BASE = "https://tienda.co"


def _pagina(url, *, status=200, enlaces=(), canonical=None, noindex=False, pedida=None, redirecciones=(), huella="", palabras=0):
    return {
        "url": url,
        "pedida": pedida or url,
        "redirecciones": list(redirecciones),
        "status": status,
        "error": "",
        "tipo": "text/html",
        "title": [],
        "meta_desc": [],
        "h1": [],
        "canonical": [url] if canonical is None else canonical,
        "robots": "noindex" if noindex else "",
        "noindex": noindex,
        "enlaces": [(e, True) for e in enlaces],
        "huella": huella,
        "palabras": palabras,
        "profundidad": 0,
    }


def _ids(resultado):
    return {h["id"]: h for h in resultado["hallazgos"]}


def test_robots_elige_el_grupo_de_googlebot_y_la_regla_mas_larga():
    leido = robots.leer(ROBOTS_SHOPIFY)
    assert leido["sitemaps"] == ["https://tienda.co/sitemap.xml"]
    google = robots.reglas_para(leido, "googlebot")
    assert not robots.permitido(f"{BASE}/privado/x", google)
    assert robots.permitido(f"{BASE}/collections/zapatos?sort_by=price", google)
    general = robots.reglas_para(leido, "otrobot")
    assert not robots.permitido(f"{BASE}/collections/zapatos?sort_by=price", general)
    assert robots.permitido(f"{BASE}/collections/zapatos?sort_by=permitido", general)
    assert not robots.permitido(f"{BASE}/collections/rojo+azul", general)
    assert robots.permitido(f"{BASE}/products/zapato", general)


def test_robots_con_fin_de_ruta():
    reglas = robots.reglas_para(robots.leer("User-agent: *\nDisallow: /*.pdf$"), "googlebot")
    assert not robots.permitido(f"{BASE}/ficha.pdf", reglas)
    assert robots.permitido(f"{BASE}/ficha.pdf?v=2", reglas)


def test_lee_indice_y_urlset_tambien_en_gzip():
    indice = b"""<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap><loc>https://tienda.co/sitemap_products_1.xml</loc></sitemap></sitemapindex>"""
    assert leer_sitemap(indice) == (["https://tienda.co/sitemap_products_1.xml"], [])
    urlset = b"""<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://tienda.co/products/a</loc><lastmod>2026-09-01</lastmod></url><url><loc>https://tienda.co/products/b</loc></url></urlset>"""
    hijos, urls = leer_sitemap(gzip.compress(urlset))
    assert hijos == []
    assert urls == [{"url": "https://tienda.co/products/a", "lastmod": "2026-09-01"}, {"url": "https://tienda.co/products/b", "lastmod": ""}]


def test_plantillas_y_parametros_de_shopify():
    assert plataforma('<link href="https://cdn.shopify.com/x.css">') == "shopify"
    assert plantilla(f"{BASE}/", "shopify") == "portada"
    assert plantilla(f"{BASE}/products/olla", "shopify") == "producto"
    assert plantilla(f"{BASE}/collections/hogar/products/olla", "shopify") == "producto_en_coleccion"
    assert plantilla(f"{BASE}/en/collections/hogar", "shopify") == "coleccion"
    assert plantilla(f"{BASE}/blogs/news/receta", "shopify") == "articulo"
    assert plantilla(f"{BASE}/servicios/seo", "otra") == "/servicios/"
    assert parametros(f"{BASE}/collections/hogar?filter.v.price.gte=10&utm_source=x") == [
        ("filter.v.price.gte", "filtro"), ("utm_source", "seguimiento"),
    ]
    assert es_paginacion(f"{BASE}/collections/hogar?page=2")
    assert not es_paginacion(f"{BASE}/collections/hogar?page=2&sort_by=price")


def test_compactar_lee_redirecciones_noindex_y_enlaces_internos():
    fila = {
        "url": "https://www.tienda.co/products/olla",
        "status": 200,
        "redirect_urls": "http://tienda.co/products/olla@@https://tienda.co/products/olla",
        "redirect_reasons": "301@@301",
        "canonical": "/products/olla",
        "meta_robots": "noindex, follow",
        "links_url": "https://www.tienda.co/a#x@@https://otro.com/b@@https://tienda.co/c",
        "links_nofollow": "False@@False@@True",
        "body_text": "  Olla   de aluminio ",
        "resp_headers_Content-Type": "text/html",
    }
    pagina = compactar(fila, "www.tienda.co")
    assert pagina["pedida"] == "http://tienda.co/products/olla"
    assert len(pagina["redirecciones"]) == 2
    assert pagina["canonical"] == ["https://www.tienda.co/products/olla"]
    assert pagina["noindex"]
    assert pagina["enlaces"] == [("https://www.tienda.co/a", True), ("https://tienda.co/c", False)]
    assert pagina["palabras"] == 3
    assert es_interna("https://tienda.co/x", "www.tienda.co")


def test_leer_cabeza_encuentra_canonical_y_robots_en_cualquier_orden():
    html = '<head><link href="/p/a" rel="canonical"><meta content="noindex" name="robots"></head>'
    assert leer_cabeza(html, f"{BASE}/p/a?x=1") == ([f"{BASE}/p/a"], "noindex")


def test_sitemap_con_error_noindex_redireccion_y_canonical_ajeno():
    paginas = [
        _pagina(f"{BASE}/", enlaces=[f"{BASE}/a", f"{BASE}/b", f"{BASE}/c", f"{BASE}/d2"]),
        _pagina(f"{BASE}/a", status=404),
        _pagina(f"{BASE}/b", noindex=True),
        _pagina(f"{BASE}/d2", pedida=f"{BASE}/d", redirecciones=[(f"{BASE}/d", "301")]),
        _pagina(f"{BASE}/c", canonical=[f"{BASE}/otra"]),
    ]
    resultado = indexacion.analizar(
        paginas, [f"{BASE}/", f"{BASE}/a", f"{BASE}/b", f"{BASE}/c", f"{BASE}/d"], {}, [], portada=f"{BASE}/",
    )
    ids = _ids(resultado)
    assert ids["sitemap_con_error"]["afectadas"] == 1
    assert ids["sitemap_noindex"]["ejemplos"] == [{"url": f"{BASE}/b"}]
    assert ids["sitemap_redirige"]["ejemplos"][0]["final"] == f"{BASE}/d2"
    assert ids["sitemap_no_canonica"]["ejemplos"][0]["canonical"] == f"{BASE}/otra"
    assert ids["sitemap_con_error"]["origen_criterio"] == "Google"
    assert [h["id"] for h in resultado["hallazgos"]][0] == "sitemap_con_error"


def test_enlace_roto_usa_la_verificacion_y_cuenta_origenes():
    paginas = [
        _pagina(f"{BASE}/", enlaces=[f"{BASE}/x", f"{BASE}/viejo"]),
        _pagina(f"{BASE}/x", enlaces=[f"{BASE}/viejo"]),
    ]
    verificadas = {f"{BASE}/viejo": {"estado": "ok", "status": 404, "final": f"{BASE}/viejo", "cadena": [], "canonical": []}}
    rotos = _ids(indexacion.analizar(paginas, [f"{BASE}/", f"{BASE}/x"], verificadas, [], portada=f"{BASE}/"))["enlaces_rotos"]
    assert rotos["ejemplos"][0]["paginas_que_enlazan"] == 2
    assert indexacion.pendientes(paginas, "otra") == [f"{BASE}/viejo"]


def test_cadena_de_redirecciones_y_canonical_a_url_que_redirige():
    paginas = [_pagina(f"{BASE}/", enlaces=[f"{BASE}/v1"]), _pagina(f"{BASE}/p", canonical=[f"{BASE}/v1"])]
    verificadas = {f"{BASE}/v1": {"estado": "ok", "status": 200, "final": f"{BASE}/v3",
                                  "cadena": [(f"{BASE}/v1", 301), (f"{BASE}/v2", 301)], "canonical": []}}
    ids = _ids(indexacion.analizar(paginas, [f"{BASE}/"], verificadas, [], portada=f"{BASE}/"))
    assert ids["cadenas_redireccion"]["ejemplos"][0]["saltos"] == 2
    assert ids["cadenas_redireccion"]["origen_criterio"] == "criterio interno de Aura"
    assert ids["canonical_roto"]["ejemplos"][0]["motivo"] == "redirige"


def test_filtros_indexables_y_bloqueados_por_robots():
    reglas = robots.reglas_para(robots.leer(ROBOTS_SHOPIFY), "otrobot")
    filtro = f"{BASE}/collections/hogar?filter.p.m.color=rojo"
    orden = f"{BASE}/collections/hogar?sort_by=price"
    paginas = [_pagina(f"{BASE}/", enlaces=[filtro, orden, f"{BASE}/collections/hogar?page=2"])]
    verificadas = {filtro: {"estado": "ok", "status": 200, "final": filtro, "cadena": [], "canonical": [filtro]}}
    resultado = indexacion.analizar(paginas, [f"{BASE}/"], verificadas, reglas, portada=f"{BASE}/", plataforma_sitio="shopify")
    hallazgo = _ids(resultado)["parametros_indexables"]
    assert hallazgo["ejemplos"][0]["parametro"] == "filter.p.m.color"
    assert hallazgo["nivel"] == "inferido"
    grupo_orden = next(g for g in resultado["tablas"]["parametros"] if g["parametro"] == "sort_by")
    assert grupo_orden["bloqueadas_robots"] == 1
    assert all(g["tipo"] != "pagina" for g in resultado["tablas"]["parametros"])


def test_producto_en_coleccion_sin_canonical_al_producto():
    ruta = f"{BASE}/collections/hogar/products/olla"
    paginas = [_pagina(f"{BASE}/", enlaces=[ruta])]
    verificadas = {ruta: {"estado": "ok", "status": 200, "final": ruta, "cadena": [], "canonical": [ruta]}}
    ids = _ids(indexacion.analizar(paginas, [f"{BASE}/"], verificadas, [], portada=f"{BASE}/", plataforma_sitio="shopify"))
    assert ids["producto_en_coleccion"]["afectadas"] == 1
    bien = {ruta: {**verificadas[ruta], "canonical": [f"{BASE}/products/olla"]}}
    ids = _ids(indexacion.analizar(paginas, [f"{BASE}/"], bien, [], portada=f"{BASE}/", plataforma_sitio="shopify"))
    assert "producto_en_coleccion" not in ids


def test_huerfanas_profundas_y_fuera_del_sitemap():
    cadena = [f"{BASE}/n{i}" for i in range(1, 6)]
    paginas = [_pagina(f"{BASE}/", enlaces=[cadena[0], f"{BASE}/nueva"])]
    paginas += [_pagina(url, enlaces=[cadena[i + 1]] if i + 1 < len(cadena) else []) for i, url in enumerate(cadena)]
    paginas += [_pagina(f"{BASE}/sola"), _pagina(f"{BASE}/nueva")]
    resultado = indexacion.analizar(paginas, [f"{BASE}/", *cadena, f"{BASE}/sola"], {}, [], portada=f"{BASE}/")
    ids = _ids(resultado)
    assert ids["huerfanas"]["ejemplos"] == [{"url": f"{BASE}/sola"}]
    assert [f["clics_desde_portada"] for f in ids["profundas"]["ejemplos"]] == [4, 5]
    assert ids["fuera_del_sitemap"]["ejemplos"][0]["url"] == f"{BASE}/nueva"


def test_login_carrito_y_checkout_no_cuentan_como_enlaces():
    from aura_organic_growth.auditoria_seo.rastreo import es_interna

    host = "www.tienda.co"
    assert es_interna(f"{BASE}/collections/ollas", host)
    assert es_interna(f"{BASE}/pages/cartagena", host)
    for ruta in ("/customer_authentication/redirect?locale=es", "/account/login", "/cart", "/en/checkouts/x"):
        assert not es_interna(f"{BASE}{ruta}", host)


def test_escapes_en_minuscula_y_mayuscula_son_la_misma_url():
    from aura_organic_growth.auditoria_seo.rastreo import normalizar

    assert normalizar(f"{BASE}/products/silla-%e2%9c%a8") == normalizar(f"{BASE}/products/silla-%E2%9C%A8")


def test_retomar_vuelve_a_pedir_las_limitadas_y_gana_el_reintento(tmp_path):
    import json

    from aura_organic_growth.auditoria_seo.rastreo import paginas, ya_rastreadas

    archivo = tmp_path / "rastreo.jl"
    filas = [
        {"url": f"{BASE}/collections/ollas", "status": 429},
        {"url": f"{BASE}/products/olla", "status": 200},
        {"url": f"{BASE}/collections/ollas", "status": 200, "links_url": f"{BASE}/products/olla"},
    ]
    archivo.write_text(json.dumps(filas[0]) + "\n" + json.dumps(filas[1]) + "\n", encoding="utf-8")
    assert ya_rastreadas(archivo) == {f"{BASE}/products/olla"}
    from aura_organic_growth.auditoria_seo.rastreo import fallidas_previas

    assert fallidas_previas(archivo) == [f"{BASE}/collections/ollas"]
    with archivo.open("a", encoding="utf-8") as salida:
        salida.write(json.dumps(filas[2]) + "\n")
    coleccion = next(p for p in paginas(archivo, "tienda.co") if p["url"].endswith("/ollas"))
    assert coleccion["status"] == 200 and coleccion["enlaces"] == [(f"{BASE}/products/olla", True)]


def test_paginas_sin_respuesta_hacen_no_determinables_las_huerfanas():
    paginas = [_pagina(f"{BASE}/"), _pagina(f"{BASE}/sola")] + [_pagina(f"{BASE}/c{i}", status=429) for i in range(3)]
    sitemap = [f"{BASE}/", f"{BASE}/sola"] + [f"{BASE}/c{i}" for i in range(3)]
    verificadas = {f"{BASE}/c{i}": {"estado": "ok", "status": 200, "cadena": []} for i in range(3)}
    resultado = indexacion.analizar(paginas, sitemap, verificadas, [], portada=f"{BASE}/")
    assert "huerfanas" not in _ids(resultado)
    assert resultado["resumen"]["huerfanas_y_profundidad"].startswith("no determinable: 3 páginas")


def test_un_enlace_que_redirige_no_deja_huerfano_a_su_destino():
    paginas = [_pagina(f"{BASE}/", enlaces=[f"{BASE}/a2-key/"]), _pagina(f"{BASE}/cognita/a2-key/")]
    verificadas = {f"{BASE}/a2-key/": {"estado": "ok", "status": 200, "final": f"{BASE}/cognita/a2-key/",
                                       "cadena": [(f"{BASE}/a2-key/", 301)]}}
    resultado = indexacion.analizar(paginas, [f"{BASE}/", f"{BASE}/cognita/a2-key/"], verificadas, [], portada=f"{BASE}/")
    assert "huerfanas" not in _ids(resultado)
    assert "enlaces_a_redireccion" in _ids(resultado)


def test_un_429_es_no_determinable_y_nunca_enlace_roto():
    paginas = [_pagina(f"{BASE}/", enlaces=[f"{BASE}/a", f"{BASE}/b"]), _pagina(f"{BASE}/a", status=429)]
    verificadas = {f"{BASE}/b": {"estado": "limitada", "status": 429, "cadena": []}}
    resultado = indexacion.analizar(paginas, [f"{BASE}/", f"{BASE}/a"], verificadas, [], portada=f"{BASE}/")
    ids = _ids(resultado)
    assert "enlaces_rotos" not in ids and "sitemap_con_error" not in ids
    assert resultado["resumen"]["no_determinables"] == 2


def test_rastreo_incompleto_no_afirma_huerfanas():
    paginas = [_pagina(f"{BASE}/"), _pagina(f"{BASE}/sola")]
    sitemap = [f"{BASE}/", f"{BASE}/sola"] + [f"{BASE}/p{i}" for i in range(10)]
    resultado = indexacion.analizar(paginas, sitemap, {}, [], portada=f"{BASE}/")
    assert "huerfanas" not in _ids(resultado)
    assert resultado["resumen"]["huerfanas_y_profundidad"].startswith("no determinable")
    assert _ids(resultado)["title_vacio"]["nivel"] == "observado"


class _Respuesta:
    def __init__(self, status, cabeceras=None):
        self.status_code = status
        self.headers = cabeceras or {}
        self.is_redirect = False

    def close(self):
        pass


class _Sesion:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)

    def get(self, *args, **kwargs):
        return self.respuestas.pop(0)


def test_reintenta_el_429_con_la_espera_que_pide_el_servidor():
    from aura_organic_growth.auditoria_seo.rastreo import _pedir

    pausas = []
    sesion = _Sesion([_Respuesta(429, {"Retry-After": "7"}), _Respuesta(200)])
    assert _pedir(sesion, f"{BASE}/x", 1.0, pausas.append).status_code == 200
    assert pausas == [1.0, 7.0, 1.0]


def test_duplicados_exactos_solo_si_los_canonicals_difieren():
    paginas = [
        _pagina(f"{BASE}/", enlaces=[f"{BASE}/a", f"{BASE}/b", f"{BASE}/c"]),
        _pagina(f"{BASE}/a", huella="h1", palabras=80),
        _pagina(f"{BASE}/b", huella="h1", palabras=80),
        _pagina(f"{BASE}/c", huella="h2", palabras=80, canonical=[f"{BASE}/d"]),
        _pagina(f"{BASE}/d", huella="h2", palabras=80),
    ]
    resultado = indexacion.analizar(paginas, [f"{BASE}/"], {}, [], portada=f"{BASE}/")
    assert {f["url"] for f in resultado["tablas"]["duplicados_exactos"]} == {f"{BASE}/a", f"{BASE}/b"}
