from aura_organic_growth.analisis import siempre, unir


def test_madurez_baja_e_inventario_parcial_dejan_al_cliente():
    diagnostico = {
        "empresa": "Alterra",
        "url": "https://alterra.co",
        "dominio": "alterra.co",
        "madurez": "baja",
        "hallazgos": [{
            "id": "title_vacio",
            "tipo": "oportunidad",
            "texto": "1 página respondió sin título.",
            "nivel": "observado",
            "alcance": "sitio",
            "consecuencia": "En Google y en una respuesta de IA esa página no dice qué vende.",
        }],
    }
    auditoria = {
        "empresa": "Alterra",
        "sitio": "https://alterra.co/",
        "estado": "incompleto",
        "cobertura_sitemap": 0.93,
        "hallazgos": [{
            "id": "title_vacio",
            "tipo": "oportunidad",
            "texto": "12 páginas respondieron sin título.",
            "nivel": "observado",
            "alcance": "sitio",
            "afectadas": 12,
            "consecuencia": "En Google y en una respuesta de IA esa página no dice qué vende.",
        }, {
            "id": "huerfanas",
            "titulo": "Huérfanas",
            "nivel": "no determinable",
            "afectadas": 0,
        }],
    }
    analisis = unir(diagnostico, auditoria)
    assert analisis["en_analisis"] is True
    assert analisis["madurez"] == "baja"
    assert analisis["inventario"]["conserva_cliente"] is True
    assert analisis["inventario"]["estado"] == "incompleto"
    assert analisis["oportunidades"][0]["afectadas"] == 12
    assert [h["id"] for h in analisis["oportunidades"]] == ["title_vacio"]
    assert analisis["hallazgos"][0]["id"] == "title_vacio"
    assert analisis["madurez"] == "baja"


def test_sin_auditoria_conserva_la_oportunidad_de_la_portada():
    analisis = unir({
        "empresa": "Taller",
        "url": "https://taller.cl",
        "madurez": "baja",
        "hallazgos": [{
            "id": "pagina_venta_rota",
            "tipo": "oportunidad",
            "texto": "1 página de venta respondió con error.",
            "nivel": "observado",
            "alcance": "sitio",
            "consecuencia": "Quien quiere comprar llega a una página rota y se va.",
        }],
    })
    assert analisis["inventario"] == {
        "estado": "sin auditoria seo",
        "cobertura_sitemap": None,
        "conserva_cliente": True,
    }
    assert analisis["oportunidades"][0]["id"] == "pagina_venta_rota"
    assert analisis["en_analisis"] is True


def test_con_web_el_profundo_corre_en_la_misma_medicion():
    llamadas = []

    def auditar(url):
        llamadas.append(url)
        return {
            "url": url,
            "cobertura_sitemap": 1,
            "hallazgos": [{
                "id": "title_vacio",
                "tipo": "oportunidad",
                "texto": "3 páginas respondieron sin título.",
                "nivel": "observado",
                "alcance": "sitio",
                "afectadas": 3,
                "consecuencia": "En Google y en una respuesta de IA esa página no dice qué vende.",
            }],
        }

    analisis = siempre({"empresa": "X", "url": "https://x.co", "madurez": "baja", "hallazgos": []}, auditar)
    assert llamadas == ["https://x.co"]
    assert analisis["oportunidades"][0]["afectadas"] == 3
    assert analisis["en_analisis"] is True


def test_sin_web_no_dispara_el_rastreo():
    def auditar(url):
        raise AssertionError(url)

    analisis = siempre({"empresa": "Y", "url": "", "madurez": "sin web", "hallazgos": []}, auditar)
    assert analisis["inventario"]["estado"] == "sin auditoria seo"


def test_si_el_rastreo_falla_el_cliente_sigue():
    def auditar(url):
        raise RuntimeError("timeout")

    analisis = siempre({"empresa": "Z", "url": "https://z.co", "hallazgos": []}, auditar)
    assert analisis["en_analisis"] is True
    assert analisis["inventario"]["estado"] == "error"
