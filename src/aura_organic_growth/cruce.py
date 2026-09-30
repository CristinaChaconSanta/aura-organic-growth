"""Cruce del lote con Apollo por dominio. El nombre no se usa.

«Terra» dentro de «Terralink» es un falso positivo. El dominio, no.
"""

from __future__ import annotations

import unicodedata
from urllib.parse import urlparse

PRECAUCION_CATCHALL = "usar con precaución"
IDIOMA_ES = frozenset({"chile", "mexico", "colombia"})
IDIOMA_PT = frozenset({"brazil", "brasil"})


def plano(texto: str) -> str:
    base = unicodedata.normalize("NFKD", (texto or "").casefold())
    return "".join(ch for ch in base if not unicodedata.combining(ch)).strip()


def dominio_de(valor: str) -> str:
    texto = (valor or "").strip()
    if not texto:
        return ""
    if "://" not in texto:
        texto = "https://" + texto
    host = (urlparse(texto).hostname or "").casefold()
    return host.removeprefix("www.")


def idioma_de(pais: str) -> str:
    clave = plano(pais)
    if clave in IDIOMA_PT:
        return "pt-BR"
    if clave in IDIOMA_ES:
        return "es"
    return "sin dato"


def es_catchall(contacto: dict) -> bool:
    status = plano(str(contacto.get("email_status") or ""))
    catch = plano(str(contacto.get("catchall") or ""))
    return status in {"catch-all", "catchall"} or catch in {"catch-all", "catchall"}


def elegir_contacto(candidatos: list[dict]) -> dict | None:
    """Un contacto por dominio. Verificado y no catch-all gana. Empate: el email."""
    con_email = [c for c in candidatos if str(c.get("email") or "").strip()]
    if not con_email:
        return None

    def clave(contacto: dict) -> tuple:
        status = plano(str(contacto.get("email_status") or ""))
        verificado = 0 if status == "verified" else 1
        catch = 1 if es_catchall(contacto) else 0
        return (verificado, catch, str(contacto.get("email") or "").casefold())

    elegido = sorted(con_email, key=clave)[0]
    return {
        "nombre": str(elegido.get("nombre") or "").strip() or None,
        "cargo": str(elegido.get("cargo") or "").strip() or None,
        "email": str(elegido["email"]).strip(),
        "email_status": str(elegido.get("email_status") or "").strip() or None,
        "precaucion": PRECAUCION_CATCHALL if es_catchall(elegido) else None,
    }


def indexar_por_dominio(contactos: list[dict]) -> dict[str, list[dict]]:
    grupos: dict[str, list[dict]] = {}
    for contacto in contactos:
        dominio = dominio_de(str(contacto.get("website") or ""))
        if not dominio:
            continue
        grupos.setdefault(dominio, []).append(contacto)
    return grupos


def contacto_del_dominio(dominio: str, contactos: list[dict]) -> dict | None:
    """Solo el host exacto. No busca el nombre de la empresa."""
    return elegir_contacto(indexar_por_dominio(contactos).get(dominio_de(dominio), []))
