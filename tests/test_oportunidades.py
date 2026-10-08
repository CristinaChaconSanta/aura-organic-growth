from aura_organic_growth.hallazgos import cinco
from aura_organic_growth.oportunidades import de_paginas, desde_respuesta, es_pagina_de_venta

BASE = "https://tienda.co"


def _pagina(url, *, status=200, title=(), meta=(), h1=(), tipo="text/html"):
    return {
        "url": url, "status": status, "tipo": tipo,
        "title": list(title), "meta_desc": list(meta), "h1": list(h1),
    }


def test_title_meta_y_h1_vacios_son_oportunidad_observada():
    paginas = [
        _pagina(f"{BASE}/", title=["Inicio"], meta=["Vende ollas"]),
        _pagina(f"{BASE}/products/olla"),
    ]
    ids = {h["id"]: h for h in de_paginas(paginas, plataforma_sitio="shopify")}
    assert ids["title_vacio"]["afectadas"] == 1
    assert ids["title_vacio"]["nivel"] == "observado"
    assert ids["title_vacio"]["ejemplos"] == [{"url": f"{BASE}/products/olla"}]
    assert ids["meta_vacia"]["afectadas"] == 1
    assert ids["h1_vacio"]["afectadas"] == 2
    assert all(h["tipo"] == "oportunidad" for h in ids.values())


def test_la_portada_rota_es_oportunidad_y_un_429_no():
    paginas = [
        _pagina(f"{BASE}/", status=500),
        _pagina(f"{BASE}/products/olla", status=404),
        _pagina(f"{BASE}/products/silla", status=429),
        _pagina(f"{BASE}/blog/nota", status=404),
    ]
    ids = {h["id"]: h for h in de_paginas(paginas, plataforma_sitio="shopify")}
    assert {fila["url"] for fila in ids["pagina_venta_rota"]["ejemplos"]} == {f"{BASE}/", f"{BASE}/products/olla"}
    assert "title_vacio" not in ids
    assert es_pagina_de_venta(f"{BASE}/servicios/seo")
    assert not es_pagina_de_venta(f"{BASE}/blog/nota")


def test_sin_respuesta_no_se_inventa_el_vacio():
    assert de_paginas([_pagina(f"{BASE}/", status=None)]) == []
    pagina = desde_respuesta(f"{BASE}/", 200, "<html><title>Ollas</title><h1>Ollas de aluminio</h1></html>")
    assert de_paginas([pagina])[0]["id"] == "meta_vacia"
    assert desde_respuesta(f"{BASE}/", None, None)["status"] is None
    assert de_paginas([desde_respuesta(f"{BASE}/", None, None)]) == []


def test_la_oportunidad_entra_en_los_cinco_con_la_velocidad():
    orden = cinco([
        {"texto": "El origen tarda.", "alcance": "sitio", "tipo": "velocidad", "nivel": "observado", "consecuencia": "Quien entra espera."},
        de_paginas([_pagina(f"{BASE}/")])[0],
        {"texto": "La ficha no trae precio.", "alcance": "pagina", "tipo": "ausencia", "nivel": "observado", "consecuencia": "Una ficha."},
    ])
    assert [item["tipo"] for item in orden] == ["velocidad", "oportunidad", "ausencia"]
