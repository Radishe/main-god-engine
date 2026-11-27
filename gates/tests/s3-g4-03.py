"""S3-G4-03: attribute-zero is not an erasure state (00 §6 / D16).

config/states.json must register the non-erasure state as distinguishable,
and the ledger's permanent_death must stay false on attribute depletion.
Uses the real Engine with an incomplete settlement (no invented rules).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit
sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine

ID = "S3-G4-03"


def main():
    cfg = ROOT / "config" / "states.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "states.json missing")
    d = json.loads(cfg.read_text(encoding="utf-8"))
    if d.get("non_erasure_state") != "distinguishable":
        return emit(ID, "FAIL", "non-erasure state not distinguishable")

    base = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    manifest = {"instance_id": "F1", "reincarnator_id": base["reincarnator_id"],
                "completion": "failure", "credit_delta": 0,
                "ability_ids": [], "item_ids": [], "idempotency_key": "S3-G4-03"}
    eng = Engine(base)
    eng.settle(manifest, task_volume=20)
    after = eng.ledger().as_dict()
    if after.get("permanent_death") is not False:
        return emit(ID, "FAIL", "attribute depletion set permanent_death=%r" % after.get("permanent_death"))
    if set(after) != set(base):
        return emit(ID, "FAIL", "ledger fields drifted after depletion")

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g4-03.json").write_text(json.dumps(
        {"non_erasure_state": "distinguishable", "permanent_death": False,
         "field_set_unchanged": True}, ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "depletion is non-erasure; no extra ledger fields")


if __name__ == "__main__":
    sys.exit(main())
