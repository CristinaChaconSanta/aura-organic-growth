"""Los 10 leads con mejor score. Sin PFS. El país se guarda tal como está."""

from __future__ import annotations

import json
from pathlib import Path

from aura_organic_growth.lead_intel import ORGANIC_ROOT, refuse_write

DESTINO = ORGANIC_ROOT / "data" / "lotes" / "seleccion.json"


def es_pfs(empresa: str, dominio: str = "") -> bool:
    texto = f"{empresa} {dominio}".casefold().replace(" ", "")
    return "pfsrealty" in texto or "pfsrealtygroup" in texto


def _pais(valor) -> str:
    texto = str(valor or "").strip()
    return texto or "sin dato"


def seleccionar(filas: list[dict], n: int = 10) -> list[dict]:
    """Una ficha por lead: la de mayor score. PFS no entra."""
    mejor: dict[int, dict] = {}
    for fila in filas:
        lead = fila.get("leads") or {}
        lead_id = fila.get("lead_id")
        score = fila.get("score")
        if lead_id is None or score is None:
            continue
        empresa = str(lead.get("empresa") or "").strip()
        dominio = str(lead.get("dominio") or "")
        if es_pfs(empresa, dominio):
            continue
        fecha = str(fila.get("fecha") or "")
        actual = mejor.get(lead_id)
        if actual and (score < actual["score"] or (score == actual["score"] and fecha <= actual["fecha"])):
            continue
        mejor[lead_id] = {
            "lead_id": lead_id,
            "empresa": empresa or "sin dato",
            "pais": _pais(lead.get("pais")),
            "ciudad": str(lead.get("ciudad") or "").strip() or "sin dato",
            "url": str(lead.get("url") or "").strip(),
            "dominio": dominio.strip(),
            "industria": str(lead.get("industria") or "").strip() or "sin dato",
            "score": int(score),
            "fecha": fecha,
        }
    orden = sorted(mejor.values(), key=lambda item: (-item["score"], item["empresa"].casefold()))
    return orden[:n]


def descargar_fichas(get, tamano: int = 80) -> list[dict]:
    """get(offset, tamano) devuelve una página. Corta cuando la página viene corta."""
    filas: list[dict] = []
    offset = 0
    while True:
        pagina = list(get(offset, tamano) or [])
        filas.extend(pagina)
        if len(pagina) < tamano:
            return filas
        offset += tamano


def guardar(lote: list[dict], path: Path | None = None) -> Path:
    destino = path or DESTINO
    refuse_write(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(lote, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino
