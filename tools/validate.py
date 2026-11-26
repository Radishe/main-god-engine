"""Settlement manifest validation CLI (S4-G1-01 / S4-G1-03).

MINIMAL MAINTAINER SKELETON. P2 owns the full six-variant validation
(src/contract/ + tools/validate*). This entry point exists so CI has a
blocking step that runs from day one; P2 extends it without changing its path
(config/paths.json validation_cli) or the CI wiring.

Exit 0 = manifest valid; non-zero = rejected (error names the field).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    # No manifest argument in CI wiring: validate the canonical F4 fixture.
    fixture = ROOT / "gates" / "fixtures" / "f4-settlement.json"
    if not fixture.is_file():
        print("validate: fixture missing", file=sys.stderr)
        return 1
    manifest = json.loads(fixture.read_text(encoding="utf-8"))
    try:
        from src.core.settlement import check_manifest
        from src.core.scoring import is_enabled
        check_manifest(manifest, scoring_enabled=is_enabled())
    except Exception as exc:
        print("validate: invalid_field %s" % exc, file=sys.stderr)
        return 1
    print("validate: F4 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
