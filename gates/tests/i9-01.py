"""I9: D21 tier scale — coefficient/band closure and tier coefficient wiring.

Global invariant: the shared tier table must stay self-consistent
coefficient(n)=2^(n-1), band_low(n)=1000*2^(n-1), band_low/coefficient==1000,
and settle() must actually apply the tier coefficient (D20 formula closed).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.scoring import tier_coefficient
from src.core.ledger import Engine

ID = "I9-01"


def main():
    cfg = json.loads((ROOT / "config" / "tiers.json").read_text(encoding="utf-8"))
    tiers = cfg["tiers"]
    if cfg["novice"]["coefficient"] != 0.5:
        return emit(ID, "FAIL", "novice coefficient != 0.5")
    for t in tiers:
        n = t["tier"]
        if abs(t["coefficient"] - 2 ** (n - 1)) > 1e-9:
            return emit(ID, "FAIL", "tier %d coefficient != 2^(n-1)" % n)
        if t["band_low"] != 1000 * 2 ** (n - 1):
            return emit(ID, "FAIL", "tier %d band_low mismatch" % n)
        if abs(t["band_low"] / t["coefficient"] - cfg["base_low"]) > 1e-9:
            return emit(ID, "FAIL", "tier %d closure broken" % n)
    if tiers[-1]["coefficient"] != 512.0 or tiers[-1]["band_low"] != 512000:
        return emit(ID, "FAIL", "tier 10 endpoints wrong (want 512.0 / 512000)")

    # settle() must apply the tier coefficient: higher tier -> larger payout
    base = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    c1 = Engine(base).settle(f4, tier=1).as_dict()["credits"]
    c2 = Engine(base).settle(f4, tier=2).as_dict()["credits"]
    if c2 <= c1:
        return emit(ID, "FAIL", "tier coefficient not applied in settle")
    return emit(ID, "PASS", "10 tiers closed (ratio=1000); settle tier1=%d tier2=%d" % (c1, c2))


if __name__ == "__main__":
    sys.exit(main())
