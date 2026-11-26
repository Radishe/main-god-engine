"""S1-G3-03: instance-internal state does not leak (00 §4).

After sequence A (F1->F2->F1) settles, loading F2 must see an admission snapshot
equal to the ending ledger and containing NONE of F1's local axis keys.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine
import src.loader as loader
import src.notary as notary

ID = "S1-G3-03"


def main():
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    f1 = loader.load(ROOT / "content" / "instances" / "F1" / "instance.json")
    f2 = loader.load(ROOT / "content" / "instances" / "F2" / "instance.json")

    eng = Engine(ledger)
    for i, iid in enumerate(("F1", "F2", "F1")):
        eng.settle(dict(f4, instance_id=iid, idempotency_key="G3-03-%d" % i))
    end_ledger = eng.ledger().as_dict()

    ok, markers, snap = notary.admit(f2, end_ledger)
    if not ok or not notary.steps_complete(markers):
        return emit(ID, "FAIL", "F2 admission failed")
    if snap != end_ledger:
        return emit(ID, "FAIL", "admission snapshot != ending ledger")
    leaked = set(f1["axes"]) & set(snap)
    if leaked:
        return emit(ID, "FAIL", "F1 axes leaked into F2 snapshot: %s" % sorted(leaked))

    ev = ROOT / "evidence" / "s1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-03.json").write_text(
        json.dumps({"end_ledger": end_ledger, "leaked_axes": []}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return emit(ID, "PASS", "snapshot equals ending ledger; no F1 axis leak")


if __name__ == "__main__":
    sys.exit(main())
