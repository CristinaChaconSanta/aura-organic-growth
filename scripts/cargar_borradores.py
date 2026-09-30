"""Carga el lote y los contactos de Apollo en organic_borradores.

Cruza por dominio. No redacta. No envía. No escribe en aura-lead-intelligence.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aura_organic_growth.cruce import dominio_de  # noqa: E402
from aura_organic_growth.lead_intel import lead_intel_root  # noqa: E402
from aura_organic_growth.staging import armar_lote  # noqa: E402
from aura_organic_growth.supabase_rest import pedir  # noqa: E402

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MIGRACION = ROOT / "supabase" / "migrations" / "001_organic_borradores.sql"


def _columna(ref: str) -> int:
    letras = "".join(ch for ch in ref if ch.isalpha())
    numero = 0
    for ch in letras:
        numero = numero * 26 + (ord(ch.upper()) - 64)
    return numero - 1


def _texto_celda(celda, compartidas: list[str]) -> str:
    if celda.get("t") == "inlineStr":
        return "".join(nodo.text or "" for nodo in celda.findall(".//m:t", NS))
    valor = celda.find("m:v", NS)
    if valor is None or valor.text is None:
        return ""
    if celda.get("t") == "s":
        return compartidas[int(valor.text)]
    return valor.text


def leer_apollo(path: Path) -> list[dict]:
    lock = path.parent / f"~${path.name}"
    if lock.exists():
        raise RuntimeError(f"{path.name} está abierto en Excel. No leí nada.")
    with zipfile.ZipFile(path) as libro:
        compartidas = []
        if "xl/sharedStrings.xml" in libro.namelist():
            raiz = ET.fromstring(libro.read("xl/sharedStrings.xml"))
            for nodo in raiz.findall("m:si", NS):
                compartidas.append("".join(t.text or "" for t in nodo.findall(".//m:t", NS)))
        hoja = ET.fromstring(libro.read("xl/worksheets/sheet1.xml"))
    filas = []
    for fila in hoja.findall("m:sheetData/m:row", NS):
        celdas: dict[int, str] = {}
        for celda in fila.findall("m:c", NS):
            celdas[_columna(celda.get("r") or "A1")] = _texto_celda(celda, compartidas)
        if celdas:
            filas.append(celdas)
    if not filas:
        return []
    ancho = max(max(fila) for fila in filas) + 1
    encabezados = [filas[0].get(i, "").strip() for i in range(ancho)]
    salida = []
    for fila in filas[1:]:
        crudo = {encabezados[i]: fila.get(i, "") for i in range(ancho) if encabezados[i]}
        nombre = f"{crudo.get('First Name', '').strip()} {crudo.get('Last Name', '').strip()}".strip()
        salida.append({
            "website": crudo.get("Website", ""),
            "email": crudo.get("Email", ""),
            "email_status": crudo.get("Email Status", ""),
            "catchall": crudo.get("Primary Email Catch-all Status", ""),
            "nombre": nombre,
            "cargo": crudo.get("Title", ""),
        })
    return salida


def _apollo() -> Path:
    hallados = sorted(lead_intel_root().glob("Leads_PrimeraEtapa*.xlsx"))
    if not hallados:
        raise FileNotFoundError("no está el export de Apollo en aura-lead-intelligence")
    return hallados[0]


def _lote() -> tuple[list[dict], dict[str, dict], str]:
    carpeta = ROOT / "data" / "lotes"
    seleccion = json.loads((carpeta / "seleccion.json").read_text(encoding="utf-8"))
    resumenes = sorted(carpeta.glob("resumen-*.json"))
    if not resumenes:
        return seleccion, {}, "sin dato"
    path = resumenes[-1]
    fecha = path.stem.removeprefix("resumen-")
    mediciones = {}
    for fila in json.loads(path.read_text(encoding="utf-8")):
        dominio = ""
        for lead in seleccion:
            if lead.get("empresa") == fila.get("empresa") and lead.get("pais") == fila.get("pais"):
                dominio = dominio_de(str(lead.get("dominio") or ""))
                break
        if dominio:
            mediciones[dominio] = fila
    return seleccion, mediciones, fecha


def _hipotesis() -> str:
    perfil = json.loads((ROOT / "profiles" / "aura-organic.json").read_text(encoding="utf-8"))
    for item in perfil.get("hipotesis_periodo") or []:
        if item.get("activa") and item.get("enunciado"):
            return str(item["enunciado"]).strip()
    return "sin dato"


def _existentes() -> set[int]:
    resp = pedir("GET", "/rest/v1/organic_borradores", params={"select": "lead_id"})
    if resp.status_code == 404:
        raise SystemExit(
            f"Falta la tabla organic_borradores. Corre {MIGRACION} en el SQL Editor de Supabase. No cargué nada."
        )
    resp.raise_for_status()
    return {int(fila["lead_id"]) for fila in resp.json()}


def main() -> None:
    seleccion, mediciones, fecha = _lote()
    filas = armar_lote(seleccion, mediciones, leer_apollo(_apollo()), hipotesis=_hipotesis(), fecha=fecha)
    ya = _existentes()
    nuevas = [fila for fila in filas if int(fila["lead_id"]) not in ya]
    if nuevas:
        resp = pedir(
            "POST",
            "/rest/v1/organic_borradores",
            headers={"Content-Type": "application/json", "Prefer": "return=minimal"},
            json=nuevas,
        )
        if resp.status_code == 404:
            raise SystemExit(
                f"Falta la tabla organic_borradores. Corre {MIGRACION} en el SQL Editor de Supabase. No cargué nada."
            )
        resp.raise_for_status()
    for fila in filas:
        marca = fila["contacto"].get("precaucion") or "email sin precaución"
        print(
            f"{fila['empresa']} ({fila['idioma']}) hallazgos={len(fila['hallazgos'])} {marca}",
            flush=True,
        )
    print(f"nuevas={len(nuevas)} ya_estaban={len(filas) - len(nuevas)}", flush=True)


if __name__ == "__main__":
    main()
