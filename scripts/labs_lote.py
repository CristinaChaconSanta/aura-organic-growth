"""Guarda Labs de cada lead del lote. No redacta y no envía.

Chile, México y Brasil salen del país de la ficha. El archivo queda en
data/lotes/labs-lote-FECHA.json. cargar_borradores.py lo lee por dominio.
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

from aura_organic_growth.labs import consultar, hallazgo_de_labs  # noqa: E402

HOY = date.today().isoformat()


def main() -> None:
    seleccion = json.loads((ROOT / "data" / "lotes" / "seleccion.json").read_text(encoding="utf-8"))
    registros = []
    for lead in seleccion:
        registro = consultar(str(lead.get("dominio") or ""), str(lead.get("pais") or ""), hoy=date.fromisoformat(HOY))
        registros.append(registro)
        hallazgo = "con hallazgo" if hallazgo_de_labs(registro) else registro.get("razon") or "sin ese hallazgo"
        print(
            f"{lead.get('empresa')} ({registro.get('pais')}) palabras={len(registro.get('palabras') or [])} "
            f"dominios={len(registro.get('dominios') or [])} {hallazgo}",
            flush=True,
        )
    destino = ROOT / "data" / "lotes" / f"labs-lote-{HOY}.json"
    destino.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"guardado {destino.name} leads={len(registros)}", flush=True)


if __name__ == "__main__":
    main()
