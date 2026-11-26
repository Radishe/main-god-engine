"""S1-G2-02: only a settlement manifest can change the ledger.

SPEC (00 §4 S1-G2-02): submit F4 to F3; credits = before + (engine-computed
D20 payout from structured claims), and every other field deep-equals the prior
state. The instance's credit_delta is NOT the source — this is the核心 of D18.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine
from src.core.scoring import decode_claims, compute_payout

ID = "S1-G2-02"


def main():
    fixture_dir = ROOT / "gates" / "fixtures"
    ledger_before = json.loads((fixture_dir / "f3-ledger.json").read_text(encoding="utf-8"))
    manifest = json.loads((fixture_dir / "f4-settlement.json").read_text(encoding="utf-8"))

    engine = Engine(ledger_before)
    view = engine.settle(manifest)
    after = view.as_dict()  # plain containers; the view itself stays deep-frozen

    # D20: expected payout is RECOMPUTED from claims, not copied from credit_delta
    payout = compute_payout(decode_claims(manifest))
    expected = dict(ledger_before)
    expected["credits"] = ledger_before["credits"] + payout
    if after != expected:
        return emit(ID, "FAIL", "ledger mismatch: got %r expected %r" % (after, expected))
    if ledger_before["credits"] != 1000:
        return emit(ID, "FAIL", "source fixture was mutated")
    return emit(ID, "PASS", "credits %d+%d(D20 payout)=%d; other fields deep-equal" % (
        ledger_before["credits"], payout, after["credits"]))


if __name__ == "__main__":
    sys.exit(main())
