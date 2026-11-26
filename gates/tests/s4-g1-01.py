"""S4-G1-01: validation CLI rejects all six illegal settlement variants.

invariant test; depends on the CLI existing, not on gameplay numbers.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G1-01"


def main():
    cfg = ROOT / "config" / "paths.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/paths.json not registered by S0")
    paths = json.loads(cfg.read_text(encoding="utf-8"))
    cli = paths.get("validation_cli")
    if not cli or not (ROOT / cli).is_file():
        return emit(ID, "FAIL", "validation CLI not implemented; expected red phase")
    return emit(ID, "FAIL", "six-variant assertion not implemented yet; expected red phase")


if __name__ == "__main__":
    sys.exit(main())
