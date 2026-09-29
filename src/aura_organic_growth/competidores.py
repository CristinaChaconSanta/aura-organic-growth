"""Dominios que se repiten en las búsquedas, y la velocidad de campo de cada uno.

La comparación usa LCP de usuarios reales. Sin ese dato no se dice que
el sitio está bien. Places por categoría y ciudad es una búsqueda aparte,
compartida por ciudad, y solo deja place_id.
"""

from __future__ import annotations

DIRECTORIOS = (
    "yelp.", "paginasamarillas", "doctoralia.", "tripadvisor.", "yellowpages.",
    "foursquare.", "hotfrog.", "cylex.",
)
MARKETPLACES = (
    "mercadolibre.", "amazon.", "ebay.", "olx.", "falabella.", "rappi.",
)
MEDIOS = (
    "eltiempo.", "elpais.", "bbc.", "forbes.", "latercera.", "emol.",
    "infobae.", "expansion.",
)


def clase_dominio(host: str) -> str:
    nombre = host.casefold()
    if any(marca in nombre for marca in DIRECTORIOS):
        return "directorio"
    if any(marca in nombre for marca in MARKETPLACES):
        return "marketplace"
    if any(marca in nombre for marca in MEDIOS):
        return "medio"
    return "negocio"


def repetidos(resultados: list[dict], dominio_propio: str = "") -> dict:
    """resultados: [{consulta, dominios: [host, ...]} en el orden del SERP."""
    if not resultados:
        return {"status": "sin dato", "razon": "sin resultados de búsqueda", "dominios": []}
    propio = dominio_propio.casefold().removeprefix("www.")
    cuenta: dict[str, int] = {}
    for fila in resultados:
        vistos = set()
        for host in fila.get("dominios") or []:
            limpio = str(host).casefold().removeprefix("www.")
            if not limpio or limpio == propio or limpio in vistos:
                continue
            vistos.add(limpio)
            cuenta[limpio] = cuenta.get(limpio, 0) + 1
    orden = sorted(cuenta, key=lambda host: (-cuenta[host], host))
    grupos = {"directorio": [], "marketplace": [], "medio": [], "negocio": []}
    for host in orden:
        grupos[clase_dominio(host)].append({"dominio": host, "apariciones": cuenta[host]})
    return {"status": "ok", "dominios": grupos}


def comparar_velocidad(propio: dict, otros: list[dict]) -> dict:
    """propio y otros traen dominio y lcp_ms de campo, o None."""
    def fila(item: dict) -> dict:
        lcp = item.get("lcp_ms")
        if lcp is None:
            return {"dominio": item.get("dominio"), "lcp": "sin datos de campo"}
        return {"dominio": item.get("dominio"), "lcp_ms": lcp, "nivel": "observado"}

    return {"propio": fila(propio), "competidores": [fila(item) for item in otros]}
