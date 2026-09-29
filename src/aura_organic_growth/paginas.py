"""Páginas que faltan: servicio × ciudad × intención, si ninguna URL responde.

Con una sola portada no se declara que el sitio no tiene la página.
"""

from __future__ import annotations


def _plano(texto: str) -> str:
    return (
        texto.casefold()
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )


def _blob(pagina: dict) -> str:
    return _plano(" ".join(str(pagina.get(campo) or "") for campo in ("url", "title", "h1")))


def responde(consulta: dict, pagina: dict) -> bool:
    blob = _blob(pagina)
    servicio = _plano(str(consulta.get("servicio") or ""))
    ciudad = _plano(str(consulta.get("ciudad") or ""))
    if not servicio or servicio not in blob:
        return False
    intencion = consulta.get("intencion")
    if intencion == "precio":
        return "precio" in blob
    if intencion == "mejor":
        return "mejor" in blob and ciudad in blob
    return ciudad in blob


def faltan(consultas: list[dict], paginas: list[dict], *, cobertura: str) -> dict:
    if not consultas:
        return {"status": "sin dato", "razon": "sin consultas", "paginas": []}
    if cobertura != "sitio" or not paginas:
        return {
            "status": "no determinable",
            "razon": "la muestra no cubre el sitio",
            "nivel": "no determinable",
            "paginas": [],
        }
    ausentes = []
    for consulta in consultas:
        if any(responde(consulta, pagina) for pagina in paginas):
            continue
        ausentes.append({
            "consulta": consulta.get("consulta"),
            "intencion": consulta.get("intencion"),
            "nivel": "observado",
            "detalle": "ninguna URL de la muestra responde servicio, ciudad e intención",
        })
    return {"status": "ok", "paginas": ausentes}
