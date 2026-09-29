from aura_organic_growth.paginas import faltan, responde


def test_la_portada_no_alcanza_para_decir_que_falta():
    consultas = [{"servicio": "dentista", "ciudad": "Lima", "intencion": "servicio_ciudad", "consulta": "dentista en Lima"}]
    paginas = [{"url": "https://yo.com/", "title": "Inicio", "h1": "Bienvenida"}]
    assert faltan(consultas, paginas, cobertura="portada")["status"] == "no determinable"


def test_falta_la_pagina_de_precio_si_el_sitio_no_la_tiene():
    consultas = [
        {"servicio": "dentista", "ciudad": "Lima", "intencion": "servicio_ciudad", "consulta": "dentista en Lima"},
        {"servicio": "dentista", "ciudad": "Lima", "intencion": "precio", "consulta": "precio dentista"},
    ]
    paginas = [
        {"url": "https://yo.com/dentista-en-lima", "title": "Dentista en Lima", "h1": "Dentista en Lima"},
    ]
    resultado = faltan(consultas, paginas, cobertura="sitio")
    assert resultado["paginas"] == [{
        "consulta": "precio dentista",
        "intencion": "precio",
        "nivel": "observado",
        "detalle": "ninguna URL de la muestra responde servicio, ciudad e intención",
    }]
    assert responde(consultas[0], paginas[0])
