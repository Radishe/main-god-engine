"""S2-G3-03: death produces no undefined ledger state (00 §5 / D16).

D16: death = exit and settle as incomplete; no revive; no extra asset loss.
After a death settlement the ledger field set must equal F3's, and the
permanent-death marker must stay false (exit_and_settle is not erasure).

No engine edit: uses the real Engine.settle() path with a failure manifest.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine

ID = "S2-G3-03"


def main():
    base = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    states = json.loads((ROOT / "config" / "states.json").read_text(encoding="utf-8"))
    if states.get("death_flow") != "exit_and_settle":
        return emit(ID, "FAIL", "D16 death_flow drift: %r" % states.get("death_flow"))

    # death = exit and settle as incomplete (failure manifest, no asset claim)
    death = {"instance_id": "F1", "reincarnator_id": base["reincarnator_id"],
             "completion": "failure", "credit_delta": 0,
             "ability_ids": [], "item_ids": [],
             "idempotency_key": "S2-G3-03-DEATH"}
    eng = Engine(base)
    eng.settle(death, task_volume=40)  # engine-computed incomplete deduction
    after = eng.ledger().as_dict()

    # no new/unregistered ledger fields
    if set(after) != set(base):
        return emit(ID, "FAIL", "field set drift after death: %s vs %s" % (
            sorted(after), sorted(base)))
    # exit_and_settle is not erasure: permanent_death stays false
    if after.get("permanent_death") is not False:
        return emit(ID, "FAIL", "permanent_death=%r after exit_and_settle (want False)" %
                    after.get("permanent_death"))
    # reincarnator id continuity
    if after.get("reincarnator_id") != base["reincarnator_id"]:
        return emit(ID, "FAIL", "reincarnator id changed after death")

    ev = ROOT / "evidence" / "s2"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-03.json").write_text(
        json.dumps({"death_flow": states["death_flow"], "fields": sorted(after),
                    "permanent_death": after["permanent_death"],
                    "field_set_equals_f3": set(after) == set(base)},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "death settled as exit; fields unchanged, permanent_death=False (not erasure)")


if __name__ == "__main__":
    sys.exit(main())
