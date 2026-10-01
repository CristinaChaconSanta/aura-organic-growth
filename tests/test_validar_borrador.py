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

Vi que el sitio de Metrowan carga el contenido principal en 4.8 s para usuarios reales.

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
    texto = "Hola Alvaro,\n\nEl sitio tarda 4,8 segundos.\n\nCristina | Aura Studio"
    assert validar(texto, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro Valenzuela") == []


def test_rechaza_promesa_de_ranking_y_de_aparicion_en_ia():
    ranking = BORRADOR_OK + "\nTe vamos a posicionar en el primer lugar."
    ia = BORRADOR_OK + "\nChatGPT va a mencionar tu marca."
    assert "promesa_ranking" in validar(ranking, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro")
    assert "promesa_aparicion_ia" in validar(ia, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro")


def test_rechaza_automatizacion_y_nombres_que_no_estan():
    auto = BORRADOR_OK + "\nEn Aura Studio automatizamos los reportes."
    marca = "Hola Alvaro,\n\nVi que trabajan con Under Armour y el sitio tarda 4.8 s.\n\nCristina | Aura Studio"
    assert "automatizacion" in validar(auto, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro")
    razones = validar(marca, HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro")
    assert "afirmacion_fuera_de_hallazgos" in razones


def test_borrador_vacio_no_se_rechaza():
    assert validar("", HALLAZGO, empresa="Grupo Metrowan", contacto="Alvaro") == []


AI = [{
    "texto": (
        "Le preguntamos a ChatGPT «¿Qué agencia de marketing digital me recomiendas en Santiago, Chile?» "
        "y recomendó a Bigbuda, LaGencia y Urban Marketing. No mencionó a DIVE."
    ),
    "evidencia": "ChatGPT, 2026-09-30, Chile, es. Recomendó: Bigbuda, LaGencia, Urban Marketing.",
    "fuente": "Prueba en vivo con ChatGPT",
    "fecha": "2026-09-30",
    "nivel": "observado",
    "consecuencia": "Quien le pregunta a una IA por este servicio recibe a la competencia.",
}]

BORRADOR_IA = """Hola Camila,

Con una herramienta de análisis de crecimiento orgánico le preguntamos a ChatGPT qué agencia de marketing digital recomienda en Santiago, y recomendó a Bigbuda, LaGencia y Urban Marketing. No mencionó a DIVE.

¿Tiene sentido mirarlo?

Si este momento no es el indicado, con saber eso me sirve.

Cristina | Aura Studio | aurathinking.com
"""


def test_el_gancho_con_chatgpt_pasa_sin_cifras():
    assert validar(BORRADOR_IA, AI, empresa="DIVE", contacto="Camila Venegas") == []


def test_nombrar_la_ia_no_es_promesa_pero_prometer_si():
    hecho = BORRADOR_IA + "\nChatGPT no mencionó a DIVE y Gemini tampoco lo citó."
    assert "promesa_aparicion_ia" not in validar(hecho, AI, empresa="DIVE", contacto="Camila")
    for promesa in (
        "Con nosotros ChatGPT va a recomendar a DIVE.",
        "Vamos a lograr que Gemini te mencione.",
        "Te garantizamos aparecer en ChatGPT.",
        "Así aparecerás en la IA.",
    ):
        assert "promesa_aparicion_ia" in validar(BORRADOR_IA + "\n" + promesa, AI, empresa="DIVE", contacto="Camila"), promesa


def test_rechaza_jerga_y_nombres_de_herramientas():
    for palabra in (
        "ms", "milisegundos", "LCP", "HTML", "Wayback", "DataForSEO", "PageSpeed", "Serper", "Labs",
        "intersecciones", "origen", "crawler", "schema",
    ):
        razones = validar(BORRADOR_IA + f"\nSegún {palabra} hay algo.", AI, empresa="DIVE", contacto="Camila")
        assert "jerga_tecnica" in razones, palabra
    assert "jerga_tecnica" not in validar(BORRADOR_IA + "\nLa IA lo ve distinto.", AI, empresa="DIVE", contacto="Camila")
    assert "jerga_tecnica" not in validar(BORRADOR_IA + "\nSolo mensajes y términos.", AI, empresa="DIVE", contacto="Camila")


MEDIDAS = [{
    "texto": "El sitio carga el contenido principal en 4.8 s y la portada muestra 8 palabras a quien no ejecuta JavaScript. Google marca 2.5 s como bueno.",
    "evidencia": "4.8 s; 8 palabras; 2.5 s.", "fuente": "campo", "fecha": "2026-09-30",
    "nivel": "observado", "consecuencia": "Quien entra espera.",
}]


def test_un_solo_dato_medido_por_borrador():
    dos = "Hola Alvaro,\n\nEl sitio tarda 4,8 segundos y la portada muestra 8 palabras.\n\nCristina | Aura Studio"
    assert "mas_de_un_dato" in validar(dos, MEDIDAS, empresa="X", contacto="Alvaro")
    uno = "Hola Alvaro,\n\nEl sitio tarda 4,8 segundos.\n\nCristina | Aura Studio"
    assert validar(uno, MEDIDAS, empresa="X", contacto="Alvaro") == []
    umbral = "Hola Alvaro,\n\nEl sitio tarda 4,8 segundos y Google pide 2,5 s.\n\nCristina | Aura Studio"
    assert "mas_de_un_dato" not in validar(umbral, MEDIDAS, empresa="X", contacto="Alvaro")
    solo_umbral = "Hola Alvaro,\n\nGoogle pide 2,5 s.\n\nCristina | Aura Studio"
    assert "mas_de_un_dato" not in validar(solo_umbral, MEDIDAS, empresa="X", contacto="Alvaro")


def test_una_fecha_no_cuenta_como_segundo_dato():
    texto = "Hola Alvaro,\n\nEl 30 de septiembre de 2026 el sitio tardó 4,8 segundos.\n\nCristina | Aura Studio"
    assert "mas_de_un_dato" not in validar(texto, MEDIDAS, empresa="X", contacto="Alvaro")
