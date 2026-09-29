from aura_organic_growth.hallazgos import cinco, problema_mas_grave


def test_velocidad_del_sitio_va_antes_que_el_detalle_de_una_pagina():
    orden = cinco([
        {"texto": "La ficha no trae H1.", "alcance": "pagina", "tipo": "ausencia", "nivel": "observado", "consecuencia": "Una ficha."},
        {"texto": "El origen tarda.", "alcance": "sitio", "tipo": "velocidad", "nivel": "observado", "consecuencia": "Quien entra espera."},
        {"texto": "Hay enlaces rotos.", "alcance": "sitio", "tipo": "error", "nivel": "observado", "consecuencia": "Una ruta no abre."},
    ])
    assert [item["tipo"] for item in orden] == ["velocidad", "error", "ausencia"]


def test_rechaza_trafico_backlinks_ventas_y_puntaje_geo():
    orden = cinco([
        {"texto": "Tráfico estimado de 10 mil.", "alcance": "sitio", "tipo": "otro", "nivel": "inferido", "consecuencia": "x"},
        {"texto": "Backlinks totales: 40.", "alcance": "sitio", "tipo": "otro", "nivel": "observado", "consecuencia": "x"},
        {"texto": "Ventas perdidas por la demora.", "alcance": "sitio", "tipo": "velocidad", "nivel": "observado", "consecuencia": "x"},
        {"texto": "Puntaje GEO 72.", "alcance": "sitio", "tipo": "otro", "nivel": "observado", "consecuencia": "x"},
        {"texto": "Sin nivel.", "alcance": "sitio", "tipo": "error"},
    ])
    assert orden == []
    assert problema_mas_grave(orden) == "sin hallazgo medido"
