import json

from aura_organic_growth.auditoria_seo import lote
from aura_organic_growth.auditoria_seo.ejecutar import auditar


def _ficha(lead_id, empresa, dominio, url, score):
    return {"lead_id": lead_id, "score": score, "leads": {"empresa": empresa, "dominio": dominio, "url": url, "pais": "Chile"}}


def test_un_sitio_por_dominio_sin_pfs_ni_leads_sin_web():
    filas = [
        _ficha(1, "DIVE", "dive.cl", "https://dive.cl", 80),
        _ficha(2, "DIVE", "dive.cl", "https://www.dive.cl", 94),
        _ficha(3, "PFS Realty", "pfsrealty.com", "https://pfsrealty.com", 99),
        _ficha(4, "Sin web", "", "", 90),
        _ficha(5, "English UC", "uc.cl", "https://uc.cl", 70),
    ]
    sitios = lote.sitios_de_fichas(filas)
    assert [s["empresa"] for s in sitios] == ["DIVE", "English UC"]
    assert sitios[0]["score"] == 94
    assert sitios[1]["url"] == "https://english.uc.cl"


def test_los_grandes_van_al_final_del_mas_chico_al_mas_grande():
    sitios = [
        {"url": "https://grande.co", "estimado_s": 9000},
        {"url": "https://chico.cl", "estimado_s": 60},
        {"url": "https://sin-sitemap.cl", "estimado_s": None},
        {"url": "https://mediano.mx", "estimado_s": 600},
    ]
    rapidos, grandes = lote.ordenar(sitios, tope=300)
    assert [s["url"] for s in rapidos] == ["https://chico.cl", "https://sin-sitemap.cl"]
    assert [s["url"] for s in grandes] == ["https://mediano.mx", "https://grande.co"]


def test_estimacion_por_urls_del_sitemap():
    assert lote.estimar_segundos(390) == 300
    assert lote.estimar_segundos(0) is None


def test_se_retoma_si_se_corto_o_cubrio_poco():
    assert lote.incompleto(None)
    assert lote.incompleto({"cortado_por_tiempo": True, "urls_en_sitemap": 10, "cobertura_sitemap": 1.0})
    assert lote.incompleto({"urls_en_sitemap": 500, "cobertura_sitemap": 0.4})
    assert not lote.incompleto({"urls_en_sitemap": 500, "cobertura_sitemap": 0.99})
    assert not lote.incompleto({"urls_en_sitemap": 0, "cobertura_sitemap": 0.0})


def test_la_fila_del_lote_cuenta_cada_hallazgo():
    resumen = {"plataforma": "shopify", "urls_en_sitemap": 100, "cobertura_sitemap": 1.0, "paginas_rastreadas": 101,
               "hallazgos": [{"id": "duplicados_exactos", "afectadas": 12}]}
    fila = lote.fila_resumen({"empresa": "X", "dominio": "x.co", "url": "https://x.co"}, resumen, vuelta=1)
    assert fila["estado"] == "completo" and fila["en_analisis"] is True
    assert fila["hallazgos"] == {"duplicados_exactos": 12}
    parcial = lote.fila_resumen(
        {"empresa": "Alterra", "url": "https://alterra.co"},
        {"urls_en_sitemap": 500, "cobertura_sitemap": 0.93, "hallazgos": [{"id": "title_vacio", "afectadas": 4}]},
        vuelta=1,
    )
    assert parcial["estado"] == "incompleto" and parcial["en_analisis"] is True
    caido = lote.fila_resumen({"url": "https://y.co"}, None, vuelta=1, error="timeout")
    assert caido["estado"] == "error" and caido["en_analisis"] is True


def test_un_rastreo_de_hoy_completo_no_se_repite(tmp_path):
    resumen = {"urls_en_sitemap": 10, "cobertura_sitemap": 1.0, "sitio": "https://x.co/", "hallazgos": []}
    (tmp_path / "resumen.json").write_text(json.dumps(resumen), encoding="utf-8")
    assert auditar("https://x.co", salida=tmp_path, reusar=True)["sitio"] == "https://x.co/"
