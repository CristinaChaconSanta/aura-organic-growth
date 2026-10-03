"""robots.txt con la semántica de Google: comodín *, fin $, gana la regla más larga
y, si empatan, gana Allow. https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit


def leer(texto: str) -> dict:
    grupos: list[tuple[list[str], list[tuple[str, str]]]] = []
    sitemaps: list[str] = []
    agentes: list[str] = []
    reglas: list[tuple[str, str]] = []
    leyendo_agentes = False
    for linea in (texto or "").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if ":" not in linea:
            continue
        campo, valor = (parte.strip() for parte in linea.split(":", 1))
        campo = campo.casefold()
        if campo == "sitemap":
            sitemaps.append(valor)
        elif campo == "user-agent":
            if not leyendo_agentes and agentes:
                grupos.append((agentes, reglas))
                agentes, reglas = [], []
            agentes.append(valor.casefold())
            leyendo_agentes = True
        elif campo in ("allow", "disallow"):
            leyendo_agentes = False
            if agentes and valor:
                reglas.append((campo, valor))
    if agentes:
        grupos.append((agentes, reglas))
    return {"grupos": grupos, "sitemaps": sitemaps}


def reglas_para(robots: dict, agente: str = "googlebot") -> list[tuple[str, str]]:
    agente = agente.casefold()
    elegidas: list[tuple[str, str]] = []
    largo = -1
    comodin: list[tuple[str, str]] = []
    for agentes, reglas in robots.get("grupos", []):
        for nombre in agentes:
            if nombre == "*":
                comodin.extend(reglas)
            elif agente.startswith(nombre) and len(nombre) > largo:
                elegidas, largo = list(reglas), len(nombre)
            elif agente.startswith(nombre) and len(nombre) == largo:
                elegidas.extend(reglas)
    return elegidas if largo >= 0 else comodin


def _patron(regla: str) -> re.Pattern:
    fin = regla.endswith("$")
    cuerpo = re.escape(regla[:-1] if fin else regla).replace(r"\*", ".*")
    return re.compile(cuerpo + ("$" if fin else ""))


def permitido(url: str, reglas: list[tuple[str, str]]) -> bool:
    partes = urlsplit(url)
    ruta = (partes.path or "/") + (f"?{partes.query}" if partes.query else "")
    mejor: tuple[int, bool] = (-1, True)
    for tipo, valor in reglas:
        if _patron(valor).match(ruta):
            candidato = (len(valor), tipo == "allow")
            if candidato[0] > mejor[0] or (candidato[0] == mejor[0] and candidato[1]):
                mejor = candidato
    return mejor[1]
