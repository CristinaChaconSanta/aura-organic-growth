from aura_organic_growth.validar_borrador import validar

HALLAZGO = [{
    "texto": "El origen carga el contenido principal en 4.8 s para usuarios reales (campo vía PageSpeed, 2026-09-29). Google marca por encima de 4 s como lento.",
    "evidencia": "LCP 4827 ms. El origen carga el contenido principal en 4.8 s para usuarios reales (campo vía PageSpeed, 2026-09-29).",
    "fuente": "campo vía PageSpeed",
    "fecha": "2026-09-29",
    "nivel": "observado",
    "consecuencia": "Quien entra desde el celular espera antes de ver la página.",
}]

BORRADOR_OK = """Hola Alvaro,

Vi que el origen de Metrowan carga el contenido principal en 4.8 s para usuarios reales.

¿Tiene sentido mirarlo?

Si este momento no es el indicado, con saber eso me sirve.

Cristina | Aura Studio | aurathinking.com
"""


def test_acepta_la_cifra_que_esta_en_el_hallazgo():
    assert validar(BORRADOR_OK, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro Valenzuela") == []


def test_rechaza_quince_horas_sin_fuente():
    texto = BORRADOR_OK.replace(
        "en 4.8 s para usuarios reales.",
        "y una agencia recuperó más de 15 horas semanales.",
    )
    razones = validar(texto, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro Valenzuela")
    assert "cifra_sin_fuente" in razones


def test_quince_html_no_autoriza_quince_horas():
    hallazgos = [{
        "texto": "Wayback guarda 15 HTML distintos de la portada desde 2026-03-28.",
        "evidencia": "Wayback guarda 15 HTML distintos de la portada desde 2026-03-28.",
        "fuente": "Wayback CDX",
        "fecha": "2026-03-28",
        "nivel": "inferido",
    }]
    texto = "Hola Camila,\n\nWayback guarda 15 horas de la portada.\n\nCristina | Aura Studio"
    razones = validar(texto, hallazgos, empresa="English UC", contacto="Camila Venegas")
    assert "cifra_sin_fuente" in razones


def test_acepta_4_coma_8_segundos():
    texto = "Hola Alvaro,\n\nEl origen tarda 4,8 segundos.\n\nCristina | Aura Studio"
    assert validar(texto, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro Valenzuela") == []


def test_rechaza_promesa_de_ranking_y_de_aparicion_en_ia():
    ranking = BORRADOR_OK + "\nTe vamos a posicionar en el primer lugar."
    ia = BORRADOR_OK + "\nChatGPT va a mencionar tu marca."
    assert "promesa_ranking" in validar(ranking, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro")
    assert "promesa_aparicion_ia" in validar(ia, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro")


def test_rechaza_automatizacion_y_nombres_que_no_estan():
    auto = BORRADOR_OK + "\nEn Aura Studio automatizamos los reportes."
    marca = "Hola Alvaro,\n\nVi que trabajan con Under Armour y el origen tarda 4.8 s.\n\nCristina | Aura Studio"
    assert "automatizacion" in validar(auto, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro")
    razones = validar(marca, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro")
    assert "afirmacion_fuera_de_hallazgos" in razones


def test_borrador_vacio_no_se_rechaza():
    assert validar("", HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro") == []
