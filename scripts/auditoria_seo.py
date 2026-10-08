"""Auditoría SEO de sitio completo: inventario, rastreo e indexación. Costo: 0 tokens.

    python scripts/auditoria_seo.py https://www.sitio.com
    python scripts/auditoria_seo.py https://www.sitio.com --max-paginas 300   # prueba corta
    python scripts/auditoria_seo.py https://www.sitio.com --retomar           # sigue un rastreo cortado
    python scripts/auditoria_seo.py https://www.sitio.com --solo-analizar     # reusa el rastreo guardado
    python scripts/auditoria_seo.py https://www.sitio.com --tiempo-max 300    # corta a los 5 minutos

Para muchos sitios, scripts/auditoria_seo_lote.py.
El análisis de lote (correr_lote.py) llama esta auditoría en cada sitio con web.

Salida en data/auditorias/<dominio>-<fecha>/seo/: resumen.json y un CSV por revisión.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aura_organic_growth.auditoria_seo.ejecutar import auditar  # noqa: E402


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
    try:
        auditar(
            args.url,
            salida=args.salida,
            max_paginas=args.max_paginas,
            retardo=args.retardo,
            concurrencia=args.concurrencia,
            max_verificar=args.max_verificar,
            retomar=args.retomar,
            solo_analizar=args.solo_analizar,
            tiempo_max=args.tiempo_max,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
