"""Prueba con IA y lectura del sitio para IA, solo para los leads que se pidan.

Uso: python scripts/ia_lote.py [--simular] [--sin-ia=ID,ID] LEAD_ID [LEAD_ID ...]

--sin-ia: esos leads solo reciben la lectura del sitio (sin gastar en IA).

--simular muestra la pregunta de cada lead sin llamar a DataForSEO (costo 0).
Sin --simular corre ChatGPT y Gemini con el freno de saldo (menos de USD 0,10
no llama) y escribe `data/lotes/ia-lote-AAAA-MM-DD.json` y una copia del último
resumen con `ia` y `legibilidad_ia` por lead, que es lo que lee
`actualizar_hallazgos.py`. No redacta, no envía.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import correr_lote as lote  # noqa: E402
from aura_organic_growth.ia import pregunta_de  # noqa: E402
from aura_organic_growth.labs import SALDO_URL, leer_saldo  # noqa: E402


def _saldo() -> float | None:
    login, password = lote_credenciales()
    if not login:
        return None
    resp = lote.requests.get(SALDO_URL, auth=(login, password), timeout=30)
    return leer_saldo(resp.json()) if resp.status_code == 200 else None


def lote_credenciales() -> tuple[str, str]:
    import os

    return os.getenv("DATAFORSEO_LOGIN", "").strip(), os.getenv("DATAFORSEO_PASSWORD", "").strip()


def main(argv: list[str]) -> None:
    simular = "--simular" in argv
    ids = {int(a) for a in argv if a.isdigit()}
    sin_ia = {int(n) for a in argv if a.startswith("--sin-ia=") for n in a.split("=", 1)[1].split(",") if n}
    seleccion = json.loads((ROOT / "data" / "lotes" / "seleccion.json").read_text(encoding="utf-8"))
    leads = [lead for lead in seleccion if lead["lead_id"] in ids]
    if not leads:
        raise SystemExit("sin leads: pasa los lead_id")
    inicial = None if simular else _saldo()
    resultados = {}
    for lead in leads:
        url = lote.url_de(lead["url"], lead["dominio"])
        _estado, html = lote._portada(url)
        if simular:
            servicios, ciudad, origen = lote.servicio_y_ciudad(lead, lead["dominio"], html)
            print(f"{lead['empresa']} [{origen}] {pregunta_de(servicios, ciudad, lead['pais'])}", flush=True)
            continue
        if lead["lead_id"] in sin_ia:
            ia = {"status": "sin dato", "razon": "omitida por Cristina/coordinación: pregunta no confiable", "motores": []}
            legibilidad = lote.medir_legibilidad(url, html=html)
        else:
            ia, legibilidad, _ = lote._paso_ia(lead, url, html)
        resultados[lead["lead_id"]] = {"empresa": lead["empresa"], "pais": lead["pais"], "ia": ia, "legibilidad_ia": legibilidad}
        print(f"{lead['empresa']}: ia={ia.get('status')} {ia.get('razon', '')}", flush=True)
    if simular:
        return
    final = _saldo()
    destino = ROOT / "data" / "lotes" / f"ia-lote-{lote.HOY}.json"
    destino.write_text(
        json.dumps({"saldo_inicial": inicial, "saldo_final": final, "leads": resultados}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    previo = sorted((ROOT / "data" / "lotes").glob("resumen-*.json"))
    base = json.loads(previo[-1].read_text(encoding="utf-8")) if previo else []
    por_clave = {(f["empresa"], f["pais"]): f for f in base}
    for res in resultados.values():
        fila = por_clave.setdefault((res["empresa"], res["pais"]), {"empresa": res["empresa"], "pais": res["pais"]})
        fila["ia"], fila["legibilidad_ia"] = res["ia"], res["legibilidad_ia"]
    (ROOT / "data" / "lotes" / f"resumen-{lote.HOY}.json").write_text(
        json.dumps(list(por_clave.values()), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saldo {inicial} -> {final}; guardado {destino.name}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
