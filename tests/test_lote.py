from aura_organic_growth.lote import es_pfs, guardar, seleccionar


def _fila(lead_id, score, empresa, pais, fecha="2026-09-01", dominio="", ciudad=""):
    return {
        "lead_id": lead_id,
        "score": score,
        "fecha": fecha,
        "leads": {
            "empresa": empresa,
            "pais": pais,
            "ciudad": ciudad,
            "dominio": dominio,
            "url": f"https://{dominio}" if dominio else "",
            "industria": "servicios",
        },
    }


def test_diez_mejores_sin_pfs_y_con_pais():
    filas = [_fila(1, 99, "PFS Realty Group", "United States", dominio="pfsrealty.com")]
    filas += [_fila(i, 100 - i, f"Empresa {i}", "Chile" if i % 2 else "", ciudad="Santiago") for i in range(2, 14)]
    filas.append(_fila(2, 50, "Empresa 2", "Chile", fecha="2026-01-01"))
    lote = seleccionar(filas)
    assert len(lote) == 10
    assert all(not es_pfs(item["empresa"], item["dominio"]) for item in lote)
    assert lote[0]["empresa"] == "Empresa 2"
    assert lote[0]["score"] == 98
    assert lote[0]["pais"] == "sin dato"
    assert any(item["pais"] == "sin dato" for item in lote)
    assert all("email" not in item for item in lote)


def test_guarda_fuera_del_repo_hermano(tmp_path):
    destino = guardar([{"empresa": "DIVE", "pais": "Chile"}], tmp_path / "seleccion.json")
    assert destino.read_text(encoding="utf-8").count("Chile") == 1
