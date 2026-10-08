"""Auditoría SEO de un sitio. La llama el análisis junto con el diagnóstico."""

from __future__ import annotations

import csv
import json
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import requests

from aura_organic_growth.auditoria_seo import indexacion, inventario, rastreo, robots
from aura_organic_growth.auditoria_seo.lote import incompleto
from aura_organic_growth.auditoria_seo.plantillas import plataforma
from aura_organic_growth.lead_intel import ORGANIC_ROOT


def _pedir_con_reintento(http: requests.Session, url: str, intentos: int = 3) -> requests.Response | None:
    for intento in range(intentos):
        try:
            return http.get(url, headers={"User-Agent": rastreo.UA}, timeout=30)
        except requests.RequestException:
            time.sleep(10 * (intento + 1))
    return None


def _escribir_csv(ruta: Path, filas: list[dict]) -> None:
    if not filas:
        return
    columnas = list(dict.fromkeys(k for fila in filas for k in fila))
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


def auditar(
    url: str,
    *,
    salida: Path | None = None,
    max_paginas: int = 30_000,
    retardo: float = 0.25,
    concurrencia: int = 4,
    max_verificar: int = 3000,
    retomar: bool = False,
    solo_analizar: bool = False,
    tiempo_max: int = 0,
    reusar: bool = False,
) -> dict:
    """Rastrea el sitio y devuelve el resumen. Con reusar, un rastreo de hoy ya completo no se repite."""
    inicio = time.time()
    portada = rastreo.normalizar(url if urlsplit(url).path else url.rstrip("/") + "/")
    host = urlsplit(portada).netloc
    destino = salida or ORGANIC_ROOT / "data" / "auditorias" / f"{rastreo.host_base(host)}-{date.today().isoformat()}" / "seo"
    destino.mkdir(parents=True, exist_ok=True)
    previo = destino / "resumen.json"
    if reusar and not retomar and previo.exists():
        guardado = json.loads(previo.read_text(encoding="utf-8"))
        if not incompleto(guardado):
            return guardado
        retomar = True

    http = requests.Session()
    texto_robots = _pedir_con_reintento(http, f"{urlsplit(portada).scheme}://{host}/robots.txt")
    if texto_robots is None:
        raise RuntimeError(f"{host} no respondió robots.txt en 3 intentos: sin saber sus reglas no se rastrea")
    leido = robots.leer(texto_robots.text if texto_robots.ok else "")
    reglas = robots.reglas_para(leido, "googlebot")
    resp = http.get(portada, headers={"User-Agent": rastreo.UA}, timeout=60)
    sitio = plataforma(resp.text, dict(resp.headers))

    mapas = leido["sitemaps"] or [f"{urlsplit(portada).scheme}://{host}/sitemap.xml"]
    inv = inventario.inventario(mapas, session=http)
    urls_sitemap = [fila["url"] for fila in inv["urls"]]
    print(f"plataforma {sitio}; {len(urls_sitemap)} URLs en {len(inv['sitemaps'])} sitemaps", flush=True)

    archivo = destino / "rastreo.jl"
    cortado = False
    if not solo_analizar:
        inicio_rastreo = time.time()
        rastreo.rastrear(
            [portada] + urls_sitemap,
            archivo,
            host=host,
            retardo=retardo,
            concurrencia=concurrencia,
            max_paginas=max_paginas,
            retomar=retomar,
            tiempo_max=tiempo_max,
        )
        cortado = bool(tiempo_max) and time.time() - inicio_rastreo >= tiempo_max * 0.95
    if not archivo.exists():
        archivo.touch()
    paginas = list(rastreo.paginas(archivo, host))
    print(f"rastreadas {len(paginas)} páginas en {time.time() - inicio:.0f}s", flush=True)

    por_verificar = indexacion.pendientes(paginas, sitio, tope=max_verificar)
    verificadas = rastreo.verificar(
        por_verificar, reglas, session=http, concurrencia=min(concurrencia, 2), espera=max(retardo, 1.0),
    )
    print(f"verificados {len(verificadas)} enlaces", flush=True)

    resultado = indexacion.analizar(paginas, urls_sitemap, verificadas, reglas, portada=portada, plataforma_sitio=sitio)
    for viejo in destino.glob("*.csv"):
        viejo.unlink()
    for nombre, filas in resultado["tablas"].items():
        _escribir_csv(destino / f"{nombre}.csv", filas)
    resumen = {
        "fecha": date.today().isoformat(),
        "sitio": portada,
        "plataforma": sitio,
        "sitemaps": inv["sitemaps"],
        "robots_sitemaps": leido["sitemaps"],
        "duracion_s": round(time.time() - inicio),
        "cortado_por_tiempo": cortado,
        **resultado["resumen"],
        "hallazgos": resultado["hallazgos"],
    }
    previo.write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for hallazgo in resultado["hallazgos"]:
        print(f"- {hallazgo['titulo']}: {hallazgo['afectadas']} ({hallazgo['nivel']})", flush=True)
    print(previo, flush=True)
    return resumen
