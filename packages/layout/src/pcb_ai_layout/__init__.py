"""Phase B layout package — place/route under DRC gates."""

from pcb_ai_layout.backend import (
    LayoutBackend,
    LayoutNotImplemented,
    LayoutPlanner,
    NullLayoutBackend,
)
from pcb_ai_layout.grid_backend import GridLayoutBackend
from pcb_ai_layout.service import LayoutJobResult, load_design_from_source, run_layout_job

__version__ = "0.1.0"

__all__ = [
    "GridLayoutBackend",
    "LayoutBackend",
    "LayoutJobResult",
    "LayoutNotImplemented",
    "LayoutPlanner",
    "NullLayoutBackend",
    "load_design_from_source",
    "run_layout_job",
    "__version__",
]
