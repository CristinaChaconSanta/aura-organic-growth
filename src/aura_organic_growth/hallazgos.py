"""Cinco hallazgos, por consecuencia. Cada uno dice de dónde sale.

Nunca entran como hecho: tráfico estimado, backlinks totales, ventas
perdidas ni un puntaje GEO.
"""

from __future__ import annotations

NIVELES = ("observado", "inferido", "no determinable")
_PROHIBIDO = (
    "trafico estimado", "tráfico estimado", "backlinks", "ventas perdidas",
    "puntaje geo", "geo score", "puntuacion geo", "puntuación geo",
)


def _plano(texto: str) -> str:
    return texto.casefold()


def prohibido(texto: str) -> bool:
    plano = _plano(texto)
    return any(marca in plano for marca in _PROHIBIDO)


# La prueba con IA va primero: es el gancho. Sigue la lectura del sitio para IA.
ORDEN_IA = ("ia_prueba", "ia_fuentes", "ia_js", "ia_robots", "ia_schema", "ia_llms")


def _clave(hallazgo: dict) -> tuple[int, int, int]:
    tipo_ia = str(hallazgo.get("tipo") or "")
    if tipo_ia in ORDEN_IA:
        return 0, ORDEN_IA.index(tipo_ia), 0
    grupo, tipo = _clave_sitio(hallazgo)
    return 1, grupo, tipo


def _clave_sitio(hallazgo: dict) -> tuple[int, int]:
    alcance = 0 if hallazgo.get("alcance") == "sitio" else 1
    tipo = {"velocidad": 0, "error": 1}.get(str(hallazgo.get("tipo") or ""), 2)
    if alcance == 1:
        tipo = 2
    return alcance, tipo


def cinco(hallazgos: list[dict]) -> list[dict]:
    validos = []
    for hallazgo in hallazgos:
        texto = str(hallazgo.get("texto") or "").strip()
        nivel = hallazgo.get("nivel")
        if not texto or nivel not in NIVELES or prohibido(texto) or prohibido(str(hallazgo.get("consecuencia") or "")):
            continue
        if hallazgo.get("alcance") not in ("sitio", "pagina"):
            continue
        validos.append(hallazgo)
    return sorted(validos, key=_clave)[:5]


clave_de_orden = _clave


def problema_mas_grave(hallazgos: list[dict]) -> str:
    orden = cinco(hallazgos)
    if not orden:
        return "sin hallazgo medido"
    return str(orden[0].get("texto") or "sin hallazgo medido")
