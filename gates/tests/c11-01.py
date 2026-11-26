"""C11-01: penalty executor is always the engine, never the instance.

SPEC: a failure manifest only signals the event; the instance's own credit_delta
      must NOT be applied as a deduction. The engine computes it from
      config/penalty.json using the task-volume anchor (D1/D14).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine

ID = "C11-01"


def main():
    cfg = ROOT / "config" / "penalty.json"
    if not cfg.is_file():
        return emit(ID, "PENDING", "D14 not fixed; penalty semantics undefined")
    rules = json.loads(cfg.read_text(encoding="utf-8"))
    if rules.get("executor") != "maingod_engine":
        return emit(ID, "FAIL", "penalty executor is not maingod_engine")

    base = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    legit = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    # claims are success-only evidence; a failure/aborted manifest must not carry them
    non_success = {k: v for k, v in legit.items() if k != "claims"}

    # instance tries to deduct 500 itself; without a volume anchor the engine must ignore it
    hostile = dict(non_success, completion="failure", credit_delta=-500,
                   idempotency_key="C11-hostile-001")
    engine = Engine(base)
    engine.settle(hostile)
    if engine.ledger().as_dict()["credits"] != base["credits"]:
        return emit(ID, "FAIL", "instance-supplied failure delta was applied: %r" % engine.ledger().as_dict())

    # engine, given a task volume, applies the deduction itself
    volume = 40
    engine2 = Engine(base)
    engine2.settle(dict(hostile, idempotency_key="C11-engine-002"), task_volume=volume)
    after = dict(engine2.ledger())["credits"]
    if after != base["credits"] - volume:
        return emit(ID, "FAIL", "engine deduction wrong: got %d expected %d" % (
            after, base["credits"] - volume))

    # Audit P1-1: aborted (D16 death flow) must not honour the instance's delta
    for delta in (500, -500):
        eng = Engine(base)
        eng.settle(dict(non_success, completion="aborted", credit_delta=delta,
                        idempotency_key="C11-aborted-%s" % delta))
        got = dict(eng.ledger())["credits"]
        if got != base["credits"]:
            return emit(ID, "FAIL", "aborted delta %d changed credits to %d" % (delta, got))

    # failure with a positive instance delta must also be ignored
    eng = Engine(base)
    eng.settle(dict(non_success, completion="failure", credit_delta=9999,
                    idempotency_key="C11-positive-failure"))
    if dict(eng.ledger())["credits"] != base["credits"]:
        return emit(ID, "FAIL", "failure with positive instance delta was applied")

    return emit(ID, "PASS",
                "instance delta ignored (failure/aborted); engine deducted %d from volume %d"
                % (volume, volume))


if __name__ == "__main__":
    sys.exit(main())
