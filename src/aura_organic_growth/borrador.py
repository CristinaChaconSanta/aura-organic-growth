"""Registro de cada borrador. Sirve para medir después. No redacta.

La voz, el PLU, la clasificación y la brecha se leen del repo hermano.
Este módulo solo guarda las etiquetas. El dashboard no vive aquí.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from aura_organic_growth.lead_intel import ORGANIC_ROOT, refuse_write

ANCLAS = ("riesgo", "oportunidad", "esfuerzo", "dato")
REGISTROS = ("deseabilidad", "transicion", "factibilidad")
DESTINO = ORGANIC_ROOT / "data" / "borradores" / "registro.jsonl"


def registro_borrador(
    *,
    empresa: str,
    industria: str,
    hipotesis: str,
    tipo_apertura: str,
    cta: str,
    registro: str,
    via_entrada: str = "",
    fecha_envio: str | None = None,
    fecha_reunion: str | None = None,
) -> dict:
    if tipo_apertura not in ANCLAS:
        raise ValueError(f"tipo_apertura debe ser una de {ANCLAS}")
    if registro not in REGISTROS:
        raise ValueError(f"registro debe ser uno de {REGISTROS}")
    if not hipotesis.strip() or not cta.strip():
        raise ValueError("hipotesis y cta son obligatorios")
    return {
        "empresa": empresa.strip(),
        "industria": industria.strip(),
        "hipotesis": hipotesis.strip(),
        "tipo_apertura": tipo_apertura,
        "cta": cta.strip(),
        "registro": registro,
        "byaf": "si",
        "via_entrada": via_entrada.strip(),
        "fecha_borrador": date.today().isoformat(),
        "fecha_envio": fecha_envio,
        "fecha_reunion": fecha_reunion,
        "guardado_en": datetime.now().isoformat(timespec="seconds"),
    }


def guardar_registro(fila: dict) -> Path:
    refuse_write(DESTINO)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with DESTINO.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
    return DESTINO
