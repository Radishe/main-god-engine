"""S3-G1-01: tier table has one owner and is internally consistent.

config_driven skeleton: assertion logic is written, expected values come from config.
PENDING is not skip; it keeps the gate denied until config/tiers.json is fixed.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S3-G1-01"


def main():
    cfg = ROOT / "config" / "tiers.json"
    if not cfg.is_file():
        return emit(ID, "PENDING", "config/tiers.json not fixed; skeleton stays unactivated")
    tiers = json.loads(cfg.read_text(encoding="utf-8"))
    owner = tiers.get("owner")
    model = tiers.get("growth_model")
    if not owner or not model:
        return emit(ID, "FAIL", "tiers.json missing owner or growth_model")
    return emit(ID, "FAIL", "recompute assertion not implemented yet; expected red phase")


if __name__ == "__main__":
    sys.exit(main())
