"""Auditoría SEO de sitio completo: inventario, rastreo e indexación. Costo: 0 tokens.

    python scripts/auditoria_seo.py https://www.sitio.com
    python scripts/auditoria_seo.py https://www.sitio.com --max-paginas 300   # prueba corta
    python scripts/auditoria_seo.py https://www.sitio.com --retomar           # sigue un rastreo cortado
    python scripts/auditoria_seo.py https://www.sitio.com --solo-analizar     # reusa el rastreo guardado
    python scripts/auditoria_seo.py https://www.sitio.com --tiempo-max 300    # corta a los 5 minutos

Para muchos sitios, scripts/auditoria_seo_lote.py.

Salida en data/auditorias/<dominio>-<fecha>/seo/: resumen.json y un CSV por revisión.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aura_organic_growth.auditoria_seo import indexacion, inventario, rastreo, robots  # noqa: E402
from aura_organic_growth.auditoria_seo.plantillas import plataforma  # noqa: E402


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--salida", type=Path)
    parser.add_argument("--max-paginas", type=int, default=30_000)
    parser.add_argument("--retardo", type=float, default=0.25)
    parser.add_argument("--concurrencia", type=int, default=4)
    parser.add_argument("--max-verificar", type=int, default=3000)
    parser.add_argument("--retomar", action="store_true")
    parser.add_argument("--solo-analizar", action="store_true")
    parser.add_argument("--tiempo-max", type=int, default=0, help="segundos de rastreo; 0 = sin tope")
    args = parser.parse_args()

    inicio = time.time()
    portada = rastreo.normalizar(args.url if urlsplit(args.url).path else args.url.rstrip("/") + "/")
    host = urlsplit(portada).netloc
    salida = args.salida or ROOT / "data" / "auditorias" / f"{rastreo.host_base(host)}-{date.today().isoformat()}" / "seo"
    salida.mkdir(parents=True, exist_ok=True)
    http = requests.Session()

    texto_robots = _pedir_con_reintento(http, f"{urlsplit(portada).scheme}://{host}/robots.txt")
    if texto_robots is None:
        raise SystemExit(f"{host} no respondió robots.txt en 3 intentos: sin saber sus reglas no se rastrea")
    leido = robots.leer(texto_robots.text if texto_robots.ok else "")
    reglas = robots.reglas_para(leido, "googlebot")
    resp = http.get(portada, headers={"User-Agent": rastreo.UA}, timeout=60)
    sitio = plataforma(resp.text, dict(resp.headers))

    mapas = leido["sitemaps"] or [f"{urlsplit(portada).scheme}://{host}/sitemap.xml"]
    inv = inventario.inventario(mapas, session=http)
    urls_sitemap = [fila["url"] for fila in inv["urls"]]
    print(f"plataforma {sitio}; {len(urls_sitemap)} URLs en {len(inv['sitemaps'])} sitemaps", flush=True)

    archivo = salida / "rastreo.jl"
    cortado = False
    if not args.solo_analizar:
        inicio_rastreo = time.time()
        rastreo.rastrear(
            [portada] + urls_sitemap,
            archivo,
            host=host,
            retardo=args.retardo,
            concurrencia=args.concurrencia,
            max_paginas=args.max_paginas,
            retomar=args.retomar,
            tiempo_max=args.tiempo_max,
        )
        cortado = bool(args.tiempo_max) and time.time() - inicio_rastreo >= args.tiempo_max * 0.95
    if not archivo.exists():
        archivo.touch()
    paginas = list(rastreo.paginas(archivo, host))
    print(f"rastreadas {len(paginas)} páginas en {time.time() - inicio:.0f}s", flush=True)

    por_verificar = indexacion.pendientes(paginas, sitio, tope=args.max_verificar)
    verificadas = rastreo.verificar(
        por_verificar, reglas, session=http, concurrencia=min(args.concurrencia, 2), espera=max(args.retardo, 1.0),
    )
    print(f"verificados {len(verificadas)} enlaces", flush=True)

    resultado = indexacion.analizar(paginas, urls_sitemap, verificadas, reglas, portada=portada, plataforma_sitio=sitio)
    for viejo in salida.glob("*.csv"):
        viejo.unlink()
    for nombre, filas in resultado["tablas"].items():
        _escribir_csv(salida / f"{nombre}.csv", filas)
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
    (salida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for hallazgo in resultado["hallazgos"]:
        print(f"- {hallazgo['titulo']}: {hallazgo['afectadas']} ({hallazgo['nivel']})", flush=True)
    print(salida / "resumen.json", flush=True)


if __name__ == "__main__":
    main()
