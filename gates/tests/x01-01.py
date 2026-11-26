"""X01-01: stage handoff — S1 ledger -> S2 admission snapshot (C32).

SPEC: S1 final ledger and S2 first snapshot have identical field sets, are
deep-equal, and keep the reincarnator id. This is the only cross-stage
"state not lost" assertion; no single package owns it (PX/maintainer).

Anti-forgery: two hand-written identical JSON files would satisfy a naive
deep-equality check. This test RE-DERIVES both artefacts from real runs
(Engine.settle sequence -> notary.admit) and requires byte-level agreement,
so a fake pair cannot pass.
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

ID = "X01-01"


def main():
    s1 = ROOT / "evidence" / "s1" / "final_ledger.json"
    s2 = ROOT / "evidence" / "s2" / "first_snapshot.json"
    if not (s1.is_file() and s2.is_file()):
        return emit(ID, "PENDING", "stage handoff artefacts not produced yet")

    saved_s1 = json.loads(s1.read_text(encoding="utf-8"))
    saved_s2 = json.loads(s2.read_text(encoding="utf-8"))

    # structural contract
    if set(saved_s1) != set(saved_s2):
        return emit(ID, "FAIL", "field sets differ: S1=%s S2=%s" % (
            sorted(saved_s1), sorted(saved_s2)))
    if saved_s1 != saved_s2:
        return emit(ID, "FAIL", "handoff not deep-equal")
    rid = saved_s1.get("reincarnator_id")
    if not rid or rid != saved_s2.get("reincarnator_id"):
        return emit(ID, "FAIL", "reincarnator id not continuous: %r / %r" % (
            rid, saved_s2.get("reincarnator_id")))

    # anti-forgery: re-derive both artefacts from real components
    start = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    eng = Engine(start)
    for i, iid in enumerate(("F1", "F2", "F1")):
        eng.settle(dict(f4, instance_id=iid, idempotency_key="X01-S1-%d" % i))
    derived_s1 = eng.ledger().as_dict()
    if derived_s1 != saved_s1:
        return emit(ID, "FAIL", "S1 artefact not reproducible from real settle")

    f1 = loader.load(ROOT / "content" / "instances" / "F1" / "instance.json")
    ok, markers, derived_s2 = notary.admit(f1, derived_s1)
    if not ok or not notary.steps_complete(markers):
        return emit(ID, "FAIL", "F2 admission markers incomplete: %s" % markers)
    if derived_s2 != saved_s2:
        return emit(ID, "FAIL", "S2 artefact not reproducible from real notary")

    return emit(ID, "PASS",
                "real settle->notary handoff deep-equal; id=%s; artefacts reproducible" % rid)


if __name__ == "__main__":
    sys.exit(main())
