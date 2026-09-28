"""aura-lead-intelligence entra por ruta, en solo lectura.

El código vive en el repo hermano. Copiarlo partiría las dos ofertas.
"""

from __future__ import annotations

import sys
from pathlib import Path

ORGANIC_ROOT = Path(__file__).resolve().parents[2]
LEAD_INTELLIGENCE = ORGANIC_ROOT.parent / "aura-lead-intelligence"
SNAPSHOT = "7e5b06f"


def lead_intel_root() -> Path:
    root = LEAD_INTELLIGENCE.resolve()
    if not (root / "src" / "scraper.py").is_file():
        raise FileNotFoundError(f"no está aura-lead-intelligence en {root}")
    return root


def ensure_lead_intel_on_path() -> Path:
    root = lead_intel_root()
    entry = str(root)
    if entry not in sys.path:
        sys.path.insert(0, entry)
    return root


def refuse_write(path: Path) -> None:
    """Corta cualquier escritura dentro del repo hermano."""
    resolved = path.resolve()
    root = lead_intel_root()
    if resolved == root or root in resolved.parents:
        raise PermissionError(f"solo lectura: {resolved}")
