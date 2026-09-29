"""Auditoría de posicionamiento orgánico. Mide y guarda. No inventa.

El sitemap de un portal inmobiliario puede tener decenas de miles de fichas.
Se cuentan todas. Se rastrea la oferta (inicio, landings, blog, idiomas) y
una ficha de cada sitemap de propiedades, no cada listado.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import advertools as adv
import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["PATH"] = str(ROOT / ".venv" / "bin") + os.pathsep + os.environ.get("PATH", "")
load_dotenv(ROOT / ".env")

from aura_organic_growth.lead_intel import ensure_lead_intel_on_path  # noqa: E402
from aura_organic_growth.places_ficha import ficha_google  # noqa: E402

ensure_lead_intel_on_path()
from src.senales_sitio import core_web_vitals, formulario, schema_org  # noqa: E402

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
UA = {"User-Agent": "AuraOrganicGrowth/1.0 (auditoria)"}
TODAY = date.today().isoformat()


def _get(url: str) -> bytes:
    req = Request(url, headers=UA)
    with urlopen(req, timeout=40) as resp:
        return resp.read()


def _locs(xml: bytes) -> list[tuple[str, str]]:
    root = ET.fromstring(xml)
    out = []
    for node in root.findall(f"{NS}url"):
        loc = node.find(f"{NS}loc")
        last = node.find(f"{NS}lastmod")
        if loc is not None and loc.text:
            out.append((loc.text.strip(), (last.text or "").strip() if last is not None else ""))
    return out


def inventario_sitemap(origen: str) -> dict:
    xml = _get(origen if origen.endswith(".xml") else origen.rstrip("/") + "/sitemap.xml")
    root = ET.fromstring(xml)
    mapas = [n.find(f"{NS}loc").text.strip() for n in root.findall(f"{NS}sitemap") if n.find(f"{NS}loc") is not None]
    if not mapas and root.findall(f"{NS}url"):
        mapas = [origen]
    grupos = {}
    for mapa in mapas:
        try:
            grupos[mapa] = _locs(_get(mapa))
        except Exception as exc:  # noqa: BLE001
            grupos[mapa] = [("ERROR", type(exc).__name__)]
    return {"origen": origen, "grupos": {k: v for k, v in grupos.items()}}


def elegir_urls(inv: dict) -> tuple[list[str], dict]:
    grupos = inv["grupos"]
    paginas = []
    propiedades = []
    for mapa, filas in grupos.items():
        if "propiedades" in mapa:
            propiedades.append((mapa, [u for u, _ in filas if u.startswith("http")]))
        else:
            paginas.extend(filas)

    elegidas: list[str] = []

    def add(url: str) -> None:
        if url and url.startswith("http") and url not in elegidas:
            elegidas.append(url)

    for url, _ in paginas:
        path = urlparse(url).path
        if path in ("/", "/en/", "/pt/", "/blog/", "/en/blog/", "/pt/blog/"):
            add(url)
    hubs = []
    for url, _ in paginas:
        parts = [p for p in urlparse(url).path.split("/") if p]
        if len(parts) == 1 and parts[0] not in ("blog", "en", "pt"):
            hubs.append(url)
    for url in hubs[:12]:
        add(url)
    blogs = [u for u, _ in paginas if "/blog/" in urlparse(u).path and "/en/" not in u and "/pt/" not in u]
    for url in blogs[:4]:
        add(url)
    muestra_fichas = []
    for mapa, urls in propiedades:
        if urls:
            add(urls[0])
            muestra_fichas.append({"sitemap": mapa, "url": urls[0], "declaradas": len(urls)})
    cobertura = {
        "urls_en_sitemap": sum(len([u for u, _ in filas if u.startswith("http")]) for filas in grupos.values()),
        "sitemaps": {k: len([u for u, _ in v if u.startswith("http")]) for k, v in grupos.items()},
        "rastreadas": elegidas,
        "muestra_fichas": muestra_fichas,
        "nota": "Se cuentan todas las URLs del sitemap. El rastreo on-page cubre inicio, hubs, blog y una ficha por sitemap de propiedades.",
    }
    return elegidas, cobertura


def _split(valor) -> list[str]:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return []
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return []
    return [p for p in texto.split("@@") if p.strip()]


def rastrear(urls: list[str], destino: Path) -> pd.DataFrame:
    if destino.exists():
        destino.unlink()
    adv.crawl(
        urls,
        str(destino),
        follow_links=False,
        custom_settings={
            "USER_AGENT": UA["User-Agent"],
            "ROBOTSTXT_OBEY": True,
            "DOWNLOAD_DELAY": 0.4,
            "CONCURRENT_REQUESTS": 2,
            "CLOSESPIDER_TIMEOUT": 240,
        },
    )
    return pd.read_json(destino, lines=True)


def resumir_rastreo(df: pd.DataFrame) -> dict:
    filas = []
    for _, row in df.iterrows():
        titulo = _split(row.get("title"))
        h1 = _split(row.get("h1"))
        desc = _split(row.get("meta_desc"))
        canonical = _split(row.get("canonical"))
        hreflang = _split(row.get("hreflang"))
        status = row.get("status")
        filas.append({
            "url": row.get("url"),
            "status": None if pd.isna(status) else int(status),
            "title": titulo[0] if titulo else "",
            "n_title": len(titulo),
            "meta_desc": desc[0] if desc else "",
            "h1": h1,
            "canonical": canonical[0] if canonical else "",
            "hreflang": hreflang,
            "size": None if pd.isna(row.get("size")) else int(row.get("size")),
        })
    titles = [f["title"] for f in filas if f["title"]]
    dup = {t: n for t, n in Counter(titles).items() if n > 1}
    sin_title = [f["url"] for f in filas if not f["title"]]
    sin_h1 = [f["url"] for f in filas if not f["h1"]]
    sin_desc = [f["url"] for f in filas if not f["meta_desc"]]
    errores = [f for f in filas if f["status"] and f["status"] >= 400]
    return {
        "n": len(filas),
        "paginas": filas,
        "sin_title": sin_title,
        "sin_h1": sin_h1,
        "fuente_ausencias": "html_crudo",
        "sin_meta_desc": sin_desc,
        "titles_duplicados": dup,
        "errores_http": errores,
        "con_hreflang": sum(1 for f in filas if f["hreflang"]),
    }


def imagenes(df: pd.DataFrame, tope: int = 12) -> dict:
    srcs = []
    sin_alt = 0
    con_alt = 0
    for _, row in df.iterrows():
        imgs = _split(row.get("img_src"))
        alts = _split(row.get("img_alt"))
        sin_alt += max(len(imgs) - len([a for a in alts if a.strip()]), 0)
        con_alt += len([a for a in alts if a.strip()])
        for src in imgs:
            if src.startswith("http") and src not in srcs:
                srcs.append(src)
            if len(srcs) >= tope:
                break
    pesos = []
    for src in srcs:
        try:
            r = requests.head(src, timeout=12, allow_redirects=True, headers=UA)
            largo = r.headers.get("Content-Length")
            tipo = (r.headers.get("Content-Type") or "").split(";")[0]
            if largo:
                pesos.append({"url": src, "bytes": int(largo), "tipo": tipo})
        except Exception:  # noqa: BLE001
            continue
    pesadas = [p for p in pesos if p["bytes"] > 500_000]
    return {
        "imgs_con_alt_en_rastreo": con_alt,
        "imgs_sin_alt_estimadas": sin_alt,
        "muestra_peso": pesos,
        "mas_de_500kb": pesadas,
    }


def geo_audit(url: str) -> dict:
    geo = ROOT / ".venv" / "bin" / "geo"
    proc = subprocess.run(
        [str(geo), "audit", "--url", url, "--format", "json", "--no-plugins"],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=ROOT,
    )
    if proc.returncode not in (0, 1):
        return {"status": "sin_dato", "razon": proc.stderr[-400:]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"status": "sin_dato", "razon": "json_invalido", "stdout": proc.stdout[-400:]}


def places_local(empresa: str, ciudad: str, pais: str) -> dict:
    return ficha_google(empresa, ciudad, pais)


def home_html(url: str) -> dict:
    try:
        r = requests.get(url, timeout=20, headers=UA)
        html = r.text if r.ok else ""
        return {
            "status": r.status_code,
            "final": r.url,
            "formulario": formulario(html) if html else None,
            "schema": schema_org(html) if html else None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "sin_dato", "razon": type(exc).__name__}


def main() -> None:
    origen = "https://www.pfsrealty.com/sitemap_index.xml"
    empresa = "PFS Realty Group"
    ciudad = "Weston"
    pais = "United States"
    home = "https://www.pfsrealty.com/"
    out = ROOT / "data" / "auditorias" / f"pfs-realty-{TODAY}"
    out.mkdir(parents=True, exist_ok=True)

    inv = inventario_sitemap(origen)
    urls, cobertura = elegir_urls(inv)
    (out / "cobertura.json").write_text(json.dumps(cobertura, ensure_ascii=False, indent=2), encoding="utf-8")

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_cwv = pool.submit(core_web_vitals, home)
        f_geo = pool.submit(geo_audit, home)
        f_places = pool.submit(places_local, empresa, ciudad, pais)
        f_home = pool.submit(home_html, home)
        df = rastrear(urls, out / "crawl.jl")
        cwv = f_cwv.result()
        geo = f_geo.result()
        lugar = f_places.result()
        portada = f_home.result()

    rastreo = resumir_rastreo(df)
    imgs = imagenes(df)
    from aura_organic_growth.render import comprobar_lote

    render = comprobar_lote([p["url"] for p in rastreo["paginas"]])
    payload = {
        "fecha": TODAY,
        "empresa": empresa,
        "home": home,
        "cobertura": {k: cobertura[k] for k in ("urls_en_sitemap", "nota", "muestra_fichas")},
        "rastreo": {k: rastreo[k] for k in rastreo if k != "paginas"},
        "paginas": rastreo["paginas"],
        "render": render,
        "ausencias_en_ficha": [r for r in render if r["ausencias_render"]],
        "imagenes": imgs,
        "pagespeed": cwv,
        "geo": geo,
        "places": lugar,
        "portada": portada,
        "volumen_y_posicion": "sin dato: no hay Search Console ni API de posiciones",
        "linea_base_leads": "sin dato",
        "mencion_ia_en_vivo": "sin dato: geo citations pide una key y no se corrió",
    }
    (out / "medicion.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
