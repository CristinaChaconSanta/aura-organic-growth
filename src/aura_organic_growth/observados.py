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
