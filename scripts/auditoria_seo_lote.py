"""Auditoría SEO profunda para muchos sitios. Costo: 0 en APIs (solo HTTP a cada sitio).

    python scripts/auditoria_seo_lote.py                       # los 10 de data/lotes/seleccion.json
    python scripts/auditoria_seo_lote.py --todos               # todos los leads con web de Supabase (sin PFS)
    python scripts/auditoria_seo_lote.py --urls https://a.cl,https://b.com
    python scripts/auditoria_seo_lote.py --todos --limite 30   # los 30 de mejor score

Primera vuelta: los sitios que se estiman en 5 minutos o menos, con tope de 5
minutos de rastreo. Segunda vuelta: los grandes (del más chico al más grande)
y los que se cortaron, retomados sin tope. Si se corta el lote, al volver a
correrlo se salta lo que ya quedó completo hoy (--rehacer lo repite).

Cada sitio deja su carpeta en data/auditorias/<dominio>-<fecha>/seo/ y el lote
deja data/auditorias/lote-<fecha>/lote.json y lote.csv, actualizados sitio a sitio.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aura_organic_growth.auditoria_seo import inventario, lote, rastreo, robots  # noqa: E402

HOY = date.today().isoformat()
SCRIPT = ROOT / "scripts" / "auditoria_seo.py"
CARPETA_LOTE = ROOT / "data" / "auditorias" / f"lote-{HOY}"


def _supabase_fichas() -> list[dict]:
    from dotenv import load_dotenv

    from aura_organic_growth.lote import descargar_fichas

    load_dotenv(ROOT / ".env")
    base = os.environ["SUPABASE_URL"].rstrip("/").removesuffix("/rest/v1")
    key = os.environ["SUPABASE_KEY"]
    headers = {"apikey": key, "Accept": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"

    def pagina(offset: int, tamano: int) -> list:
        resp = requests.get(
            f"{base}/rest/v1/fichas",
            headers=headers,
            params={
                "select": "score,fecha,lead_id,leads(empresa,pais,ciudad,url,dominio,industria)",
                "order": "score.desc.nullslast",
                "limit": str(tamano),
                "offset": str(offset),
            },
            timeout=40,
        )
        resp.raise_for_status()
        return resp.json()

    return descargar_fichas(pagina, tamano=100)


def _estimar(sitio: dict, http: requests.Session) -> dict:
    """Portada final (tras redirecciones) y URLs del sitemap. Si algo falla, sin estimación."""
    try:
        resp = http.get(sitio["url"], headers={"User-Agent": rastreo.UA}, timeout=40)
        portada = rastreo.normalizar(resp.url)
        partes = urlsplit(portada)
        texto = http.get(f"{partes.scheme}://{partes.netloc}/robots.txt", headers={"User-Agent": rastreo.UA}, timeout=30)
        mapas = robots.leer(texto.text if texto.ok else "")["sitemaps"] or [f"{partes.scheme}://{partes.netloc}/sitemap.xml"]
        urls = len(inventario.inventario(mapas, session=http)["urls"])
    except requests.RequestException as exc:
        return {**sitio, "estimado_s": None, "urls_estimadas": None, "nota": type(exc).__name__}
    return {**sitio, "url": portada, "urls_estimadas": urls, "estimado_s": lote.estimar_segundos(urls)}


def _carpeta(url: str) -> Path:
    return ROOT / "data" / "auditorias" / f"{rastreo.host_base(urlsplit(url).netloc)}-{HOY}" / "seo"


def _leer_resumen(url: str) -> dict | None:
    ruta = _carpeta(url) / "resumen.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def _correr(sitio: dict, *, vuelta: int, args) -> tuple[dict | None, str]:
    comando = [
        sys.executable, "-u", str(SCRIPT), sitio["url"],
        "--concurrencia", str(args.concurrencia), "--retardo", str(args.retardo),
    ]
    if vuelta == 1:
        comando += ["--tiempo-max", str(args.tope), "--max-verificar", "500"]
        limite = args.tope + 1200
    else:
        comando += ["--retomar", "--max-verificar", "3000"]
        limite = None
    try:
        proceso = subprocess.run(comando, capture_output=True, text=True, timeout=limite)
    except subprocess.TimeoutExpired:
        return _leer_resumen(sitio["url"]), "superó el tiempo de la vuelta"
    if proceso.returncode != 0:
        ultima = next((l for l in reversed(proceso.stderr.splitlines()) if l.strip()), "sin detalle")
        return None, ultima[:300]
    return _leer_resumen(sitio["url"]), ""


def _guardar(filas: list[dict]) -> None:
    CARPETA_LOTE.mkdir(parents=True, exist_ok=True)
    (CARPETA_LOTE / "lote.json").write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    columnas = list(dict.fromkeys(k for f in filas for k in f if k != "hallazgos"))
    ids = list(dict.fromkeys(h for f in filas for h in (f.get("hallazgos") or {})))
    with (CARPETA_LOTE / "lote.csv").open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas + ids)
        escritor.writeheader()
        for f in filas:
            escritor.writerow({**{k: v for k, v in f.items() if k != "hallazgos"}, **(f.get("hallazgos") or {})})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--todos", action="store_true")
    parser.add_argument("--urls")
    parser.add_argument("--limite", type=int, default=0)
    parser.add_argument("--tope", type=int, default=lote.TOPE_RAPIDO_S, help="segundos de la primera vuelta")
    parser.add_argument("--concurrencia", type=int, default=3)
    parser.add_argument("--retardo", type=float, default=0.3)
    parser.add_argument("--rehacer", action="store_true")
    args = parser.parse_args()

    if args.urls:
        sitios = [{"empresa": "sin dato", "dominio": "", "url": u.strip()} for u in args.urls.split(",") if u.strip()]
    elif args.todos:
        sitios = lote.sitios_de_fichas(_supabase_fichas())
    else:
        seleccion = json.loads((ROOT / "data" / "lotes" / "seleccion.json").read_text(encoding="utf-8"))
        sitios = lote.sitios_de_seleccion(seleccion)
    if args.limite:
        sitios = sitios[: args.limite]

    http = requests.Session()
    print(f"{len(sitios)} sitios; estimando tamaño por sitemap...", flush=True)
    sitios = [_estimar(s, http) for s in sitios]
    rapidos, grandes = lote.ordenar(sitios, tope=args.tope)
    print(f"primera vuelta: {len(rapidos)} sitios; al final: {len(grandes)} grandes", flush=True)

    previo_lote = CARPETA_LOTE / "lote.json"
    filas: dict[str, dict] = (
        {f["url"]: f for f in json.loads(previo_lote.read_text(encoding="utf-8"))} if previo_lote.exists() else {}
    )
    pendientes = list(grandes)
    for vuelta, cola in ((1, rapidos), (2, pendientes)):
        for sitio in cola:
            previo = _leer_resumen(sitio["url"])
            if previo and not args.rehacer and not lote.incompleto(previo):
                filas[sitio["url"]] = lote.fila_resumen(sitio, previo, vuelta=0)
                print(f"ya completo hoy: {sitio['url']}", flush=True)
                continue
            inicio = time.time()
            resumen, error = _correr(sitio, vuelta=vuelta, args=args)
            fila = lote.fila_resumen(sitio, resumen, vuelta=vuelta, error=error)
            filas[sitio["url"]] = fila
            _guardar(list(filas.values()))
            print(f"[vuelta {vuelta}] {sitio['url']}: {fila['estado']} en {time.time() - inicio:.0f}s {error}", flush=True)
            if vuelta == 1 and fila["estado"] != "completo":
                pendientes.append(sitio)
    _guardar(list(filas.values()))
    print(CARPETA_LOTE / "lote.csv", flush=True)


if __name__ == "__main__":
    main()
