"""Servicio y ciudad observados por Cristina, por dominio.

No se infieren de la industria de Apollo. Si el dominio no está aquí, el
servicio y la ciudad quedan «sin dato» y no se inventa una pregunta.
"""

from __future__ import annotations

from aura_organic_growth.cruce import dominio_de

OBSERVADOS = {
    "dive.cl": {
        "servicios": ["agencia de marketing digital"],
        "ciudad": "Santiago",
    },
}


def de(dominio: str) -> dict | None:
    return OBSERVADOS.get(dominio_de(dominio))

# Sitio real del lead cuando no es el que guarda Apollo (dato de Cristina).
URLS = {
    "uc.cl": "https://english.uc.cl",
}


def url_de(url: str, dominio: str) -> str:
    """Primero el sitio observado, luego la url guardada, luego el dominio."""
    return URLS.get(dominio_de(dominio) or dominio_de(url)) or url or (f"https://{dominio}" if dominio else "")
