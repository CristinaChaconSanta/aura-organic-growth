"""Señales de compra de los últimos 6 meses. Solo lo verificable.

Wayback: dos digestos distintos de la portada son un cambio observado en
el archivo, no un rediseño afirmado. crt.sh: un certificado nuevo de un
subdominio. La pauta activa no se busca: la anota Cristina.
"""

from __future__ import annotations

from datetime import date, datetime

CDX = "https://web.archive.org/cdx/search/cdx"
CRT = "https://crt.sh/"


def _hace_seis_meses(hoy: date) -> date:
    mes = hoy.month - 6
    anio = hoy.year
    if mes <= 0:
        mes += 12
        anio -= 1
    dia = min(hoy.day, 28)
    return date(anio, mes, dia)


def wayback(dominio: str, session=None, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    desde = _hace_seis_meses(hoy)
    if not dominio:
        return {"senal": "cambio de portada", "nivel": "no determinable", "detalle": "sin dominio"}
    http = session or __import__("requests")
    resp = http.get(
        CDX,
        params={
            "url": f"{dominio}/",
            "output": "json",
            "fl": "timestamp,digest,statuscode",
            "from": desde.strftime("%Y%m%d"),
            "to": hoy.strftime("%Y%m%d"),
            "filter": "statuscode:200",
            "limit": "40",
        },
        timeout=40,
    )
    if resp.status_code != 200:
        return {"senal": "cambio de portada", "nivel": "no determinable", "detalle": f"http_{resp.status_code}"}
    filas = resp.json() or []
    digestos = {fila[1] for fila in filas[1:] if len(fila) > 1 and fila[1]}
    if len(digestos) >= 2:
        return {
            "senal": "cambio de portada",
            "nivel": "inferido",
            "detalle": f"Wayback guarda {len(digestos)} HTML distintos de la portada desde {desde.isoformat()}",
        }
    if len(digestos) == 1:
        return {
            "senal": "cambio de portada",
            "nivel": "observado",
            "detalle": f"Wayback guarda un solo HTML de la portada desde {desde.isoformat()}",
        }
    return {"senal": "cambio de portada", "nivel": "no determinable", "detalle": "Wayback no devolvió capturas"}


def subdominios_nuevos(dominio: str, session=None, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    desde = _hace_seis_meses(hoy)
    if not dominio:
        return {"senal": "subdominio nuevo", "nivel": "no determinable", "nombres": []}
    http = session or __import__("requests")
    resp = http.get(CRT, params={"q": f"%.{dominio}", "output": "json"}, timeout=40)
    if resp.status_code != 200:
        return {"senal": "subdominio nuevo", "nivel": "no determinable", "detalle": f"http_{resp.status_code}", "nombres": []}
    nuevos = set()
    for entrada in resp.json() or []:
        bruto = str(entrada.get("not_before") or "")[:10]
        try:
            emitido = datetime.strptime(bruto, "%Y-%m-%d").date()
        except ValueError:
            continue
        if emitido < desde:
            continue
        for nombre in str(entrada.get("name_value") or "").splitlines():
            limpio = nombre.strip().lstrip("*.").casefold()
            if limpio in {dominio.casefold(), f"www.{dominio.casefold()}"} or not limpio.endswith(f".{dominio.casefold()}"):
                continue
            nuevos.add(limpio)
    if not nuevos:
        return {"senal": "subdominio nuevo", "nivel": "observado", "detalle": "crt.sh no muestra un subdominio nuevo en el período", "nombres": []}
    return {"senal": "subdominio nuevo", "nivel": "observado", "nombres": sorted(nuevos)}


def vacante(html: str | None) -> dict:
    if html is None:
        return {"senal": "vacante", "nivel": "no determinable", "detalle": "no se revisó una página de empleo"}
    plano = html.casefold()
    if "vacante" in plano and any(area in plano for area in ("marketing", "seo", "contenido")):
        return {"senal": "vacante", "nivel": "observado", "detalle": "la página trae vacante de marketing, SEO o contenido"}
    return {"senal": "vacante", "nivel": "no determinable", "detalle": "esa página no trae la vacante; no prueba que no exista"}


def pauta_activa(nota: str | None = None) -> dict:
    if str(nota or "").strip():
        return {"senal": "pauta activa", "nivel": "observado", "detalle": nota.strip()}
    return {
        "senal": "pauta activa",
        "nivel": "no determinable",
        "detalle": "la revisa Cristina a mano en la biblioteca de anuncios",
    }
