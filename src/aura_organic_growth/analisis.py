"""Un solo análisis por sitio: diagnóstico y auditoría SEO.

La madurez se guarda y no descarta. Un inventario incompleto tampoco saca
al cliente: entra lo que sí se midió.
"""

from __future__ import annotations

from aura_organic_growth.hallazgos import cinco, problema_mas_grave
from aura_organic_growth.oportunidades import _FICHAS

IDS_OPORTUNIDAD = frozenset(_FICHAS)


def _cobertura(auditoria: dict) -> float | None:
    if auditoria.get("cobertura_sitemap") is not None:
        return auditoria.get("cobertura_sitemap")
    resumen = auditoria.get("resumen")
    if isinstance(resumen, dict):
        return resumen.get("cobertura_sitemap")
    return None


def _hallazgos_seo(auditoria: dict) -> list[dict]:
    hallazgos = auditoria.get("hallazgos") or []
    if isinstance(hallazgos, dict):
        salida = []
        for clave, afectadas in hallazgos.items():
            if clave not in IDS_OPORTUNIDAD:
                continue
            ficha = _FICHAS[clave]
            n = int(afectadas or 0)
            if n <= 0:
                continue
            texto = ficha["uno"] if n == 1 else ficha["varios"].format(n=n)
            salida.append({
                "id": clave,
                "tipo": "oportunidad",
                "titulo": ficha["titulo"],
                "texto": texto,
                "nivel": "observado",
                "alcance": "sitio",
                "afectadas": n,
                "consecuencia": ficha["consecuencia"],
            })
        return salida
    return [h for h in hallazgos if isinstance(h, dict)]


def _es_oportunidad(hallazgo: dict) -> bool:
    return hallazgo.get("id") in IDS_OPORTUNIDAD or hallazgo.get("tipo") == "oportunidad"


def _con_texto(hallazgo: dict) -> dict:
    if hallazgo.get("texto"):
        return hallazgo
    titulo = str(hallazgo.get("titulo") or "").strip()
    if not titulo:
        return hallazgo
    afectadas = hallazgo.get("afectadas")
    texto = f"{titulo}: {afectadas}." if afectadas else titulo
    alcance = hallazgo.get("alcance")
    return {
        **hallazgo,
        "texto": texto,
        "alcance": alcance if alcance in ("sitio", "pagina") else "sitio",
        "tipo": hallazgo.get("tipo") or "error",
    }


def unir(diagnostico: dict | None = None, auditoria: dict | None = None) -> dict:
    """Un registro comercial. El cliente se queda aunque la madurez sea baja o el rastreo esté a medias."""
    diagnostico = diagnostico or {}
    auditoria = auditoria or {}
    url = str(diagnostico.get("url") or auditoria.get("url") or auditoria.get("sitio") or "")
    seo = [_con_texto(h) for h in _hallazgos_seo(auditoria)]
    diag = list(diagnostico.get("hallazgos") or [])
    del_rastreo = [h for h in seo if _es_oportunidad(h) and h.get("nivel") == "observado"]
    if del_rastreo:
        ids = {h.get("id") for h in del_rastreo}
        oportunidades = del_rastreo
        resto = [h for h in diag if h.get("id") not in ids]
        otros = [h for h in seo if h.get("id") not in ids]
    else:
        oportunidades = [h for h in diag if _es_oportunidad(h)]
        resto = [h for h in diag if not _es_oportunidad(h)]
        otros = [h for h in seo if not _es_oportunidad(h)]
    cobertura = _cobertura(auditoria)
    estado = auditoria.get("estado")
    if estado is None and cobertura is not None:
        estado = "parcial" if cobertura < 0.95 else "completo"
    elif estado is None:
        estado = "sin auditoria seo" if not auditoria else "en analisis"
    juntos = resto + oportunidades + otros
    registro = {k: v for k, v in diagnostico.items() if k not in ("hallazgos", "problema")}
    registro.update({
        "empresa": diagnostico.get("empresa") or auditoria.get("empresa") or "sin dato",
        "url": url,
        "dominio": diagnostico.get("dominio") or auditoria.get("dominio") or "",
        "madurez": diagnostico.get("madurez"),
        "en_analisis": True,
        "inventario": {
            "estado": estado,
            "cobertura_sitemap": cobertura,
            "conserva_cliente": True,
        },
        "oportunidades": oportunidades,
        "hallazgos": cinco(juntos),
        "problema": problema_mas_grave(juntos),
    })
    return registro


def siempre(diagnostico: dict, auditar) -> dict:
    """Con web, el diagnóstico y la auditoría corren en la misma medición."""
    url = str((diagnostico or {}).get("url") or "")
    if not url:
        return unir(diagnostico, None)
    try:
        auditoria = auditar(url)
    except (Exception, SystemExit) as exc:
        auditoria = {"estado": "error", "error": type(exc).__name__, "url": url, "hallazgos": []}
    return unir(diagnostico, auditoria or None)
