"""PCB Copilot KiCad 10 Action Plugin package.

Installed into KiCad's ``scripting/plugins`` directory. On import, registers
the layout action with pcbnew when running inside KiCad.
"""

from __future__ import annotations

try:
    import pcbnew  # noqa: F401
except ImportError:
    # Outside KiCad (syntax checks, unit tests) — skip registration.
    pass
else:
    from .action import register_plugin

    register_plugin()
