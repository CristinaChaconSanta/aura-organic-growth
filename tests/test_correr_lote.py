import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _sin_feed_en_red(monkeypatch):
    # El script se carga en cada test con from-import: el reemplazo va en el módulo de origen.
    monkeypatch.setattr(
        "aura_organic_growth.senales.ultima_publicacion",
        lambda html, origen, session=None, hoy=None: {"senal": "ultima publicacion", "nivel": "no determinable", "fecha": None, "url": None},
    )
    # El script carga el .env real: sin esto la pregunta la escribiría Gemini de verdad.
    monkeypatch.setattr("aura_organic_growth.ia.clave_gemini", lambda: "")
    # Madurez baja ya no corta la medición: estas llamadas no salen a la red.
    sin_dato = {"status": "sin dato", "nivel": "no determinable", "llamadas": 0, "nombres": []}
    monkeypatch.setattr("aura_organic_growth.crux.campo", lambda origen: {"nivel": "no determinable", "lcp": "sin datos de campo"})
    monkeypatch.setattr("aura_organic_growth.places_ficha.ficha_google", lambda *a, **k: sin_dato)
    monkeypatch.setattr("aura_organic_growth.entidad.entidad", lambda *a, **k: sin_dato)
    monkeypatch.setattr("aura_organic_growth.senales.wayback", lambda *a, **k: {"senal": "cambio de portada", "nivel": "no determinable"})
    monkeypatch.setattr("aura_organic_growth.senales.subdominios_nuevos", lambda *a, **k: {"senal": "subdominio nuevo", "nivel": "no determinable", "nombres": []})


RESPUESTA_IA = {
    "status": "ok", "idioma": "es", "empresa": "DIVE", "dominio": "dive.cl", "pregunta": "¿Q?",
    "fecha": "2026-09-30", "pais": "Chile",
    "motores": [{
        "motor": "ChatGPT", "status": "ok", "nivel": "observado", "idioma": "es", "menciona_lead": False,
        "recomendados": ["Bigbuda"], "fuentes_citadas": [], "listas_revisadas": [],
    }],
}


def _cargar():
    spec = importlib.util.spec_from_file_location("correr_lote_prueba", RAIZ / "scripts" / "correr_lote.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _lead(**cambios):
    return {
        "empresa": "DIVE", "pais": "Chile", "ciudad": "Santiago", "score": 90,
        "url": "https://dive.cl", "dominio": "dive.cl", "industria": "marketing", **cambios,
    }


def test_madurez_baja_sigue_en_el_analisis(monkeypatch):
    lote = _cargar()
    llamadas = []
    monkeypatch.setattr(lote, "_portada", lambda url: (200, "<html><title>Hola</title></html>"))
    monkeypatch.setattr(lote, "consultar_ia", lambda servicios, **kw: llamadas.append(("ia", servicios, kw["ciudad"])) or RESPUESTA_IA)
    monkeypatch.setattr(lote, "medir_legibilidad", lambda url, html=None: llamadas.append(("leg",)) or {
        "url": url, "fecha": "2026-09-30", "robots": {}, "llms_txt": False, "schema_tipos": [],
    })
    monkeypatch.setattr(lote, "campo", lambda origen: llamadas.append(("velocidad",)) or {"nivel": "no determinable", "lcp": "sin datos de campo"})
    for nombre in ("ficha_google", "entidad", "wayback", "subdominios_nuevos"):
        monkeypatch.setattr(lote, nombre, lambda *a, **k: {"status": "sin dato", "nivel": "no determinable", "llamadas": 0, "nombres": []})
    fila = lote._medir(_lead())
    assert fila["madurez"] == "baja" and fila["ruta"] == "auditar"
    assert fila["problema"] != "derivar a landing"
    assert ("velocidad",) in llamadas
    assert fila["ia"]["status"] == "ok"
    assert fila["hallazgos"][0]["tipo"] == "ia_prueba"
    assert any(h.get("id") == "meta_vacia" for h in fila["hallazgos"])


def test_la_ia_va_antes_que_la_velocidad_y_un_llms_txt_sube_la_madurez(monkeypatch):
    lote = _cargar()
    orden = []
    monkeypatch.setattr(lote, "_portada", lambda url: (200, "<html><title>Hola</title></html>"))
    monkeypatch.setattr(lote, "consultar_ia", lambda servicios, **kw: orden.append("ia") or RESPUESTA_IA)
    monkeypatch.setattr(lote, "medir_legibilidad", lambda url, html=None: orden.append("leg") or {
        "url": url, "fecha": "2026-09-30", "robots": {}, "llms_txt": True, "schema_tipos": [],
    })
    monkeypatch.setattr(lote, "campo", lambda origen: orden.append("velocidad") or {"nivel": "no determinable", "lcp": "sin datos de campo"})
    for nombre in ("ficha_google", "entidad", "wayback", "subdominios_nuevos"):
        monkeypatch.setattr(lote, nombre, lambda *a, **k: {"status": "sin dato", "nivel": "no determinable", "llamadas": 0, "nombres": []})
    fila = lote._medir(_lead())
    assert fila["madurez"] == "media" and fila["ruta"] == "auditar"
    assert orden[:3] == ["ia", "leg", "velocidad"]
    assert fila["hallazgos"][0]["tipo"] == "ia_prueba"


def test_sin_web_no_gasta_en_ia(monkeypatch):
    lote = _cargar()

    def no_debia(*a, **k):
        raise AssertionError("sin web no se llama a la IA")

    monkeypatch.setattr(lote, "_portada", lambda url: (None, None))
    monkeypatch.setattr(lote, "consultar_ia", no_debia)
    monkeypatch.setattr(lote, "medir_legibilidad", no_debia)
    fila = lote._medir(_lead(url="", dominio=""))
    assert fila["madurez"] == "sin web" and "ia" not in fila


def test_dominio_sin_servicio_observado_deja_la_ia_en_sin_dato(monkeypatch):
    lote = _cargar()
    monkeypatch.setenv("DATAFORSEO_LOGIN", "x")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "x")
    monkeypatch.setattr(lote, "_portada", lambda url: (200, "<html></html>"))
    monkeypatch.setattr(lote, "medir_legibilidad", lambda url, html=None: {"url": url, "fecha": "2026-09-30", "robots": {}})
    fila = lote._medir(_lead(url="https://otra.cl", dominio="otra.cl", empresa="Otra"))
    assert fila["ia"]["status"] == "sin dato"
    assert fila["ia"]["razon"] == "sin servicio o sin ciudad observados"


def test_servicio_de_la_portada_cuando_no_hay_observado(monkeypatch):
    lote = _cargar()
    recibido = {}
    monkeypatch.setattr(lote, "_portada", lambda url: (200, "<title>Clemsa – Venta de maquinarias equipos y repuestos</title>"))
    monkeypatch.setattr(lote, "consultar_ia", lambda servicios, **kw: recibido.update(servicios=servicios, **kw) or RESPUESTA_IA)
    monkeypatch.setattr(lote, "medir_legibilidad", lambda url, html=None: {"url": url, "fecha": "2026-09-30", "robots": {}})
    lote._medir(_lead(empresa="Clemsa", url="https://clemsa.cl", dominio="clemsa.cl", ciudad="San Bernardo"))
    assert recibido["servicios"] == ["venta de maquinarias equipos y repuestos"]
    assert (recibido["origen_servicio"], recibido["ciudad"]) == ("title", "San Bernardo")


def test_english_uc_usa_su_sitio_real_y_conserva_el_dominio_guardado(monkeypatch):
    lote = _cargar()
    pedidas, recibido = [], {}
    monkeypatch.setattr(lote, "_portada", lambda url: pedidas.append(url) or (200, "<h1>Cursos de inglés</h1>"))
    monkeypatch.setattr(lote, "consultar_ia", lambda servicios, **kw: recibido.update(kw) or RESPUESTA_IA)
    monkeypatch.setattr(lote, "medir_legibilidad", lambda url, html=None: pedidas.append(url) or {"url": url, "fecha": "2026-09-30", "robots": {}})
    lote._medir(_lead(empresa="English UC", url="https://uc.cl", dominio="uc.cl"))
    assert pedidas == ["https://english.uc.cl", "https://english.uc.cl"]
    assert recibido["dominio"] == "uc.cl" and recibido["origen_servicio"] == "h1"


def _con_oferta(monkeypatch, registro):
    monkeypatch.setattr("aura_organic_growth.ia.clave_gemini", lambda: "k")
    monkeypatch.setattr("aura_organic_growth.oferta.evidencia", lambda html, url, session=None, renderizar=None: [])
    monkeypatch.setattr("aura_organic_growth.oferta.oferta", lambda paginas, **kw: registro)
    lote = _cargar()
    monkeypatch.setattr(lote, "_portada", lambda url: (200, "<title>Clemsa</title>"))
    monkeypatch.setattr(lote, "medir_legibilidad", lambda url, html=None: {"url": url, "fecha": "2026-09-30", "robots": {}})
    return lote


def test_con_gemini_la_pregunta_verificada_reemplaza_la_del_title(monkeypatch):
    lote = _con_oferta(monkeypatch, {
        "status": "ok", "termino": "arriendo de maquinaria pesada",
        "preguntas": ["¿Qué empresas ofrecen arriendo de maquinaria pesada en San Bernardo?"],
    })
    recibido = {}
    monkeypatch.setattr(lote, "consultar_ia", lambda servicios, **kw: recibido.update(servicios=servicios, **kw) or dict(RESPUESTA_IA))
    fila = lote._medir(_lead(empresa="Clemsa", url="https://clemsa.cl", dominio="clemsa.cl", ciudad="San Bernardo"))
    assert recibido["pregunta"] == "¿Qué empresas ofrecen arriendo de maquinaria pesada en San Bernardo?"
    assert recibido["servicios"] == ["arriendo de maquinaria pesada"] and recibido["origen_servicio"] == "oferta"
    assert fila["ia"]["oferta"]["status"] == "ok"


def test_pregunta_no_verificada_no_gasta_en_ia(monkeypatch):
    lote = _con_oferta(monkeypatch, {"status": "sin dato", "razon": "ciudad y país no coinciden: Houston"})

    def no_debia(*a, **k):
        raise AssertionError("no debía consultar la IA")

    monkeypatch.setattr(lote, "consultar_ia", no_debia)
    fila = lote._medir(_lead(empresa="OutLoud", url="https://outloud.com", dominio="outloud.com", ciudad="Houston"))
    assert fila["ia"]["status"] == "sin dato"
    assert fila["ia"]["razon"] == "pregunta no confiable: ciudad y país no coinciden: Houston"
