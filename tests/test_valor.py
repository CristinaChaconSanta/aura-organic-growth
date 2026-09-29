from aura_organic_growth.valor import armar_interno, cargar_perfil, hipotesis_activa, precios_lanzamiento


def test_la_propuesta_no_se_cobra_y_la_hipotesis_es_una():
    perfil = cargar_perfil()
    precios = precios_lanzamiento(perfil)
    assert precios["estado"] == "pendiente de Cristina"
    assert precios["precio_del_lead"] == "sin dato"
    assert precios["ajuste_por_pais"]["filas"][1]["pais"] == "Colombia"
    assert precios["ajuste_por_pais"]["filas"][1]["factor"] == "pendiente de Cristina"
    enunciado = hipotesis_activa(perfil)
    assert enunciado.startswith("Los mensajes con ancla=dato")
    assert "pega H1" not in enunciado
    interno = armar_interno({"industria": "servicios", "precio": 400}, perfil)
    assert interno["capacidad_pago"]["precio"] == "sin dato"
    assert "400" not in str(interno["capacidad_pago"])
