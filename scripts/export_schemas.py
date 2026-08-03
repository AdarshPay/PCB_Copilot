"""Export Pydantic models to JSON Schema files under schemas/."""

from __future__ import annotations

from pathlib import Path

from pcb_ai_circuit_ir.schema_export import export_schemas


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    written = export_schemas(root / "schemas")
    for name, path in written.items():
        print(f"wrote {name} -> {path}")


if __name__ == "__main__":
    main()
