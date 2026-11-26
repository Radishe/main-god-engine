"""C25-01: erasure / non-erasure ledger semantics that D16 has settled.

SPEC (config/states.json is the single structured source of truth):
  - A7 is closed by D16; death = exit and settle, counted toward erasure.
  - no revive; lethal requires declaration.
  - erasure state is registered and distinguishable from non-erasure state.

NOT COVERED: the '曾到达 X 阶' memorial marker field is still an unratified
meta-decision. This test does NOT invent or assert its shape; it only rejects
an implementation that silently introduces such a field before ratification.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "C25-01"


def main():
    cfg = ROOT / "config" / "states.json"
    if not cfg.is_file():
        return emit(ID, "PENDING", "states.json missing; death vs erasure undefined")
    rules = json.loads(cfg.read_text(encoding="utf-8"))

    checks = {
        "death_flow": "exit_and_settle",
        "counts_toward_erasure": True,
        "revive": False,
        "lethal_requires_declaration": True,
        "erasure_state": "registered",
        "non_erasure_state": "distinguishable",
    }
    drift = ["%s=%r expected %r" % (k, rules.get(k), v)
             for k, v in checks.items() if rules.get(k) != v]
    if drift:
        return emit(ID, "FAIL", "states.json drift: " + "; ".join(drift))

    # Ledger must not carry an unratified memorial marker yet.
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    markers = [k for k in ledger if "纪念" in k or "memorial" in k.lower() or "peak" in k.lower()]
    if markers:
        return emit(ID, "FAIL", "unratified memorial marker in ledger: " + ",".join(markers))

    return emit(ID, "PASS",
                "D16 settled semantics consistent; memorial marker left unratified (not invented)")


if __name__ == "__main__":
    sys.exit(main())
