"""S1-G3-01: submission order does not change the ledger (00 §4).

Sequence A: F1 -> F2 -> F1; Sequence B: F1 -> F1 -> F2. Each starts fresh from
F3. Final ledgers must be deep-equal (commutative under the engine's rules).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine

ID = "S1-G3-01"


def run_sequence(order):
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    eng = Engine(ledger)
    for i, iid in enumerate(order):
        eng.settle(dict(f4, instance_id=iid, idempotency_key="G3-%s-%d" % (iid, i)))
    return eng.ledger().as_dict()


def main():
    a = run_sequence(["F1", "F2", "F1"])
    b = run_sequence(["F1", "F1", "F2"])
    if a != b:
        return emit(ID, "FAIL", "order changed ledger: A=%r B=%r" % (a, b))

    ev = ROOT / "evidence" / "s1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-01.json").write_text(
        json.dumps({"A_F1_F2_F1": a, "B_F1_F1_F2": b, "deep_equal": True},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "both orders converge to same final ledger")


if __name__ == "__main__":
    sys.exit(main())
