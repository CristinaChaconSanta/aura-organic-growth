"""Actualiza hallazgos en organic_borradores. No redacta y no envía.

Labs se lee del archivo ya guardado. Serper corre solo cuando hay servicio
y ciudad observados. En este lote el único es dive.cl.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from aura_organic_growth.cruce import dominio_de  # noqa: E402
from aura_organic_growth.observados import de as observado_de  # noqa: E402
from aura_organic_growth.serper import buscar  # noqa: E402
from aura_organic_growth.staging import hallazgos_de_medicion, juntar, parche_pendiente  # noqa: E402
from aura_organic_growth.supabase_rest import pedir  # noqa: E402

def _por_dominio(filas: list[dict]) -> dict[str, dict]:
    return {dominio_de(str(fila.get("dominio") or "")): fila for fila in filas if fila.get("dominio")}


def _resumen(seleccion: list[dict]) -> tuple[dict[str, dict], str]:
    carpeta = ROOT / "data" / "lotes"
    resumenes = sorted(carpeta.glob("resumen-*.json"))
    if not resumenes:
        return {}, "sin dato"
    path = resumenes[-1]
    fecha = path.stem.removeprefix("resumen-")
    por_empresa = {}
    for fila in json.loads(path.read_text(encoding="utf-8")):
        por_empresa[(fila.get("empresa"), fila.get("pais"))] = fila
    salida = {}
    for lead in seleccion:
        fila = por_empresa.get((lead.get("empresa"), lead.get("pais")))
        dominio = dominio_de(str(lead.get("dominio") or ""))
        if fila and dominio:
            salida[dominio] = fila
    return salida, fecha


def _labs() -> dict[str, dict]:
    archivos = sorted((ROOT / "data" / "lotes").glob("labs-lote-*.json"))
    if not archivos:
        return {}
    guardado = json.loads(archivos[-1].read_text(encoding="utf-8"))
    return _por_dominio(guardado if isinstance(guardado, list) else [])


def _serper(seleccion: list[dict], hoy: date) -> list[dict]:
    registros = []
    for lead in seleccion:
        dominio = dominio_de(str(lead.get("dominio") or ""))
        observado = observado_de(dominio)
        if not observado:
            registros.append({
                "dominio": dominio,
                "pais": lead.get("pais") or "sin dato",
                "fecha": hoy.isoformat(),
                "status": "sin dato",
                "razon": "sin servicio o sin ciudad observados",
                "consultas": [],
            })
            print(f"{lead.get('empresa')} serper=sin dato", flush=True)
            continue
        registro = buscar(
            observado["servicios"],
            ciudad=observado["ciudad"],
            pais=str(lead.get("pais") or ""),
            dominio=dominio,
            hoy=hoy,
        )
        registro["dominio"] = dominio
        registros.append(registro)
        for consulta in registro.get("consultas") or []:
            print(
                f"{lead.get('empresa')} «{consulta.get('consulta')}» "
                f"posición={consulta.get('posicion')} listas={len(consulta.get('listas') or [])}",
                flush=True,
            )
        if registro.get("status") != "ok":
            print(f"{lead.get('empresa')} serper={registro.get('razon')}", flush=True)
    return registros


def main() -> None:
    hoy = date.today()
    seleccion = json.loads((ROOT / "data" / "lotes" / "seleccion.json").read_text(encoding="utf-8"))
    registros = _serper(seleccion, hoy)
    destino = ROOT / "data" / "lotes" / f"serper-lote-{hoy.isoformat()}.json"
    destino.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    resumenes, fecha = _resumen(seleccion)
    labs = _labs()
    serper = _por_dominio(registros)
    actualizadas = 0
    for lead in seleccion:
        dominio = dominio_de(str(lead.get("dominio") or ""))
        hallazgos = hallazgos_de_medicion(
            juntar(resumenes.get(dominio), labs.get(dominio), serper.get(dominio)),
            fecha,
        )
        parche = parche_pendiente(hallazgos)
        if not parche:
            print(f"{lead.get('empresa')} sin hallazgo, no se toca", flush=True)
            continue
        resp = pedir(
            "PATCH",
            "/rest/v1/organic_borradores",
            params={"lead_id": f"eq.{int(lead['lead_id'])}"},
            headers={"Content-Type": "application/json", "Prefer": "return=representation"},
            json=parche,
        )
        resp.raise_for_status()
        filas = resp.json()
        if not filas:
            print(f"{lead.get('empresa')} no está en organic_borradores", flush=True)
            continue
        actualizadas += 1
        print(
            f"{lead.get('empresa')} estado={filas[0].get('estado')} hallazgos={len(filas[0].get('hallazgos') or [])}",
            flush=True,
        )
    print(f"guardado {destino.name} actualizadas={actualizadas}", flush=True)


if __name__ == "__main__":
    main()
