from datetime import date

from aura_organic_growth.madurez import clasificar

HOY = date(2026, 9, 29)


def test_sin_web_deriva_a_landing():
    resultado = clasificar(None, hoy=HOY, tiene_web=False)
    assert resultado["madurez"] == "sin web"
    assert resultado["ruta"] == "derivar a landing"


def test_portada_vacia_es_baja_y_sigue_en_el_analisis():
    resultado = clasificar("<html><title>Hola</title></html>", hoy=HOY)
    assert resultado["madurez"] == "baja"
    assert resultado["ruta"] == "auditar"


def test_analitica_sola_es_media():
    html = '<script src="https://www.googletagmanager.com/gtag/js"></script>'
    resultado = clasificar(html, hoy=HOY)
    assert resultado["madurez"] == "media"
    assert resultado["ruta"] == "auditar"
    assert resultado["evidencia"][0]["nivel"] == "observado"


def test_dos_senales_es_alta_y_el_blog_sin_fecha_no_cuenta():
    html = """
    <script src="https://js.hs-scripts.com/1.js"></script>
    <a href="/blog">Blog</a>
    """
    resultado = clasificar(html, hoy=HOY)
    assert resultado["madurez"] == "media"
    assert any(item["senal"] == "blog" and item["nivel"] == "no determinable" for item in resultado["evidencia"])


def test_blog_reciente_suma():
    html = '<script src="https://www.googletagmanager.com/gtm.js"></script><time datetime="2026-08-01">'
    resultado = clasificar(html, hoy=HOY)
    assert resultado["madurez"] == "alta"
    assert resultado["ruta"] == "auditar"


def test_portada_sin_respuesta_no_se_inventa_y_el_lead_sigue():
    resultado = clasificar(None, hoy=HOY, tiene_web=True)
    assert resultado["madurez"] == "no determinable"
    assert resultado["ruta"] == "auditar"


def test_llms_txt_o_schema_rico_no_es_madurez_baja():
    pagina = "<html><title>Terra</title></html>"
    con_llms = clasificar(pagina, hoy=HOY, llms_txt=True)
    assert con_llms["madurez"] == "media" and con_llms["ruta"] == "auditar"
    assert con_llms["evidencia"][0] == {"senal": "legibilidad IA", "nivel": "observado", "detalle": "llms.txt"}
    schema = (
        '<script type="application/ld+json">{"@graph":[{"@type":"FAQPage"},{"@type":"LocalBusiness"}]}</script>'
    )
    con_schema = clasificar(schema, hoy=HOY, llms_txt=False)
    assert con_schema["madurez"] == "media"
    assert "FAQPage" in con_schema["evidencia"][0]["detalle"]
    assert clasificar(pagina, hoy=HOY, llms_txt=False)["madurez"] == "baja"


def test_senal_de_ia_suma_una_sola_vez_con_otra_senal():
    html = '<script src="https://www.googletagmanager.com/gtag/js"></script>'
    assert clasificar(html, hoy=HOY, llms_txt=True)["madurez"] == "alta"
    schema_y_llms = '<script type="application/ld+json">{"@type":"Organization"}</script>'
    assert clasificar(schema_y_llms, hoy=HOY, llms_txt=True)["madurez"] == "media"


def test_el_feed_manda_sobre_una_fecha_suelta():
    html = '<script src="https://www.googletagmanager.com/gtm.js"></script>'
    feed = {"senal": "ultima publicacion", "nivel": "observado", "fecha": "2026-08-03", "url": "https://dive.cl/feed/"}
    resultado = clasificar(html, hoy=HOY, ultima_publicacion=feed)
    assert resultado["madurez"] == "alta"
    blog = next(e for e in resultado["evidencia"] if e["senal"] == "blog activo")
    assert blog["detalle"] == "2026-08-03 (feed https://dive.cl/feed/)"


def test_feed_sin_publicar_en_seis_meses_se_anota_y_no_suma():
    html = '<script src="https://www.googletagmanager.com/gtm.js"></script><time datetime="2026-08-01">'
    viejo = {"senal": "ultima publicacion", "nivel": "observado", "fecha": "2025-11-02", "url": "https://dive.cl/feed/"}
    resultado = clasificar(html, hoy=HOY, ultima_publicacion=viejo)
    assert resultado["madurez"] == "media"
    assert any(e["senal"] == "blog sin publicar" and "2025-11-02" in e["detalle"] for e in resultado["evidencia"])
    sin_feed = clasificar(html, hoy=HOY, ultima_publicacion={"nivel": "no determinable", "fecha": None})
    assert sin_feed["madurez"] == "alta"
