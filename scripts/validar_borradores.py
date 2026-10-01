"""Pasa el validador por cada borrador redactado. No envía.

Si hay una razón (cifra sin fuente, promesa, jerga o más de un dato), la fila
queda rechazada. Aprobar sigue siendo de Cristina.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aura_organic_growth.supabase_rest import pedir  # noqa: E402
from aura_organic_growth.validar_borrador import validar  # noqa: E402


def main() -> None:
    resp = pedir(
        "GET",
        "/rest/v1/organic_borradores",
        params={"select": "lead_id,empresa,contacto,hallazgos,borrador", "estado": "eq.redactado"},
    )
    resp.raise_for_status()
    filas = resp.json()
    rechazados = 0
    for fila in filas:
        contacto = fila.get("contacto") or {}
        razones = validar(
            fila.get("borrador") or "",
            fila.get("hallazgos") or [],
            empresa=fila.get("empresa") or "",
            contacto=str(contacto.get("nombre") or ""),
        )
        if not razones:
            print(f"{fila['empresa']}: redactado", flush=True)
            continue
        motivo = ", ".join(razones)
        parche = pedir(
            "PATCH",
            "/rest/v1/organic_borradores",
            params={"lead_id": f"eq.{fila['lead_id']}"},
            headers={"Content-Type": "application/json", "Prefer": "return=minimal"},
            json={"estado": "rechazado", "motivo_rechazo": motivo},
        )
        parche.raise_for_status()
        rechazados += 1
        print(f"{fila['empresa']}: rechazado ({motivo})", flush=True)
    print(f"revisados={len(filas)} rechazados={rechazados}", flush=True)


if __name__ == "__main__":
    main()
