"""Pone `src/` en el path para que los scripts importen el paquete `sast`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
