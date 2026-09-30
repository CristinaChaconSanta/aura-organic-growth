from aura_organic_growth.cruce import contacto_del_dominio, dominio_de, es_catchall, idioma_de
from aura_organic_growth.staging import armar_lote, hallazgos_de_medicion


def test_el_dominio_ignora_www_y_la_ruta():
    assert dominio_de("https://www.dive.cl/es") == "dive.cl"
    assert dominio_de("terraenergy.io") == "terraenergy.io"


def test_terra_no_cruza_con_terralink():
    contactos = [
        {
            "website": "https://terralink.com",
            "email": "ana@terralink.com",
            "email_status": "Verified",
            "catchall": "Not Catch-all",
            "nombre": "Ana Terra",
            "cargo": "Head of Marketing",
        },
        {
            "website": "https://www.terraenergy.io/inicio",
            "email": "emma@terraenergy.io",
            "email_status": "Verified",
            "catchall": "Not Catch-all",
            "nombre": "Emma Juarez",
            "cargo": "Head of Growth Marketing",
        },
    ]
    filas = armar_lote(
        [{
            "lead_id": 45,
            "empresa": "Terra",
            "dominio": "terraenergy.io",
            "pais": "Mexico",
            "industria": "semiconductors",
        }],
        {},
        contactos,
        hipotesis="ancla dato",
        fecha="2026-09-29",
    )
    assert filas[0]["contacto"]["email"] == "emma@terraenergy.io"
    assert filas[0]["contacto"]["precaucion"] is None
    assert filas[0]["idioma"] == "es"
    assert filas[0]["borrador"] == ""
    assert filas[0]["estado"] == "pendiente"
    assert filas[0]["fecha_envio"] is None
    assert filas[0]["fecha_reunion"] is None


def test_catchall_se_marca_y_el_verificado_gana():
    contactos = [
        {
            "website": "https://outloudmarketing.com",
            "email": "catch@outloudmarketing.com",
            "email_status": "Verified",
            "catchall": "Catch-all",
            "nombre": "Catch All",
            "cargo": "Marketing Director",
        },
        {
            "website": "https://outloudmarketing.com",
            "email": "jguizar@outloudmarketing.com",
            "email_status": "Verified",
            "catchall": "Not Catch-all",
            "nombre": "Jose Guizar",
            "cargo": "Marketing Director",
        },
    ]
    elegido = contacto_del_dominio("outloudmarketing.com", contactos)
    assert elegido["email"] == "jguizar@outloudmarketing.com"
    assert elegido["precaucion"] is None
    assert es_catchall(contactos[0]) is True


def test_si_solo_hay_catchall_se_usa_con_precaucion():
    elegido = contacto_del_dominio("https://metrowan.cl", [{
        "website": "https://metrowan.cl",
        "email": "alvaro@metrowan.cl",
        "email_status": "Verified",
        "catchall": "Catch-all",
        "nombre": "Alvaro Valenzuela",
        "cargo": "Head of Marketing",
    }])
    assert elegido["precaucion"] == "usar con precaución"
    assert elegido["email_status"] == "Verified"


def test_idioma_por_pais():
    assert idioma_de("Chile") == "es"
    assert idioma_de("México") == "es"
    assert idioma_de("Brazil") == "pt-BR"
    assert idioma_de("Brasil") == "pt-BR"
    assert idioma_de("") == "sin dato"


def test_lcp_bueno_no_inventa_hallazgo_y_el_lento_guarda_la_cifra():
    assert hallazgos_de_medicion(
        {"velocidad": {"lcp_ms": 1973, "nivel": "observado", "fuente": "campo vía PageSpeed"}, "hallazgos": []},
        "2026-09-29",
    ) == []
    hallados = hallazgos_de_medicion(
        {
            "velocidad": {"lcp_ms": 4827, "fuente": "campo vía PageSpeed"},
            "hallazgos": [{
                "texto": "El origen carga el contenido principal en 4.8 s (campo vía PageSpeed, 2026-09-29).",
                "consecuencia": "Quien entra espera.",
                "tipo": "velocidad",
                "nivel": "observado",
            }],
            "wayback": {"nivel": "no determinable", "detalle": "Wayback no devolvió capturas"},
        },
        "2026-09-29",
    )
    assert hallados[0]["evidencia"].startswith("LCP 4827 ms.")
    assert hallados[0]["fuente"] == "campo vía PageSpeed"
    assert hallados[0]["fecha"] == "2026-09-29"
    assert hallados[0]["nivel"] == "observado"
    assert len(hallados) == 1
