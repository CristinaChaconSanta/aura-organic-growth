from datetime import date

from aura_organic_growth.madurez import clasificar

HOY = date(2026, 9, 29)


def test_sin_web_deriva_a_landing():
    resultado = clasificar(None, hoy=HOY, tiene_web=False)
    assert resultado["madurez"] == "sin web"
    assert resultado["ruta"] == "derivar a landing"


def test_portada_vacia_es_baja_y_no_se_audita():
    resultado = clasificar("<html><title>Hola</title></html>", hoy=HOY)
    assert resultado["madurez"] == "baja"
    assert resultado["ruta"] == "derivar a landing"


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


def test_portada_sin_respuesta_no_se_inventa():
    resultado = clasificar(None, hoy=HOY, tiene_web=True)
    assert resultado["madurez"] == "no determinable"
    assert resultado["ruta"] == "no auditar"
