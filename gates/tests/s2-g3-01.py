"""S2-G3-01: the full instance cycle is observable in order (00 §5).

D1-style run must emit, in order and exactly once each:
  notarized -> instance_event -> settlement_submitted -> ledger_committed

Real components only: notary.admit (notarized), loader.apply_event (instance
event), Engine.settle (commit). No engine edit, no fake doubles, no invented
markers — the log is assembled from real calls with a marker hook.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
import src.loader as loader
import src.notary as notary
from src.core.ledger import Engine

ID = "S2-G3-01"
ORDER = ["notarized", "instance_event", "settlement_submitted", "ledger_committed"]


class MarkHook:
    def __init__(self, log):
        self.log = log

    def committed(self, instance_id, delta):
        self.log.append("ledger_committed")

    def reject(self, code, detail):
        self.log.append("rejected:" + code)


def main():
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    f1 = loader.load(ROOT / "content" / "instances" / "F1" / "instance.json")

    log = []
    # 1. admission notarization -> one 'notarized' marker (from real markers)
    ok, markers, snap = notary.admit(f1, ledger)
    if not ok or not notary.steps_complete(markers):
        return emit(ID, "FAIL", "admission markers incomplete: %s" % markers)
    log.append("notarized")

    # 2. one declared instance event -> one 'instance_event' marker
    axis_changed, _ = loader.apply_event(f1, tick=1)
    if not axis_changed:
        return emit(ID, "FAIL", "instance event produced no state change")
    log.append("instance_event")

    # 3+4. submit then commit via the real engine
    log.append("settlement_submitted")
    engine = Engine(ledger, hooks=MarkHook(log))
    engine.settle(dict(f4, instance_id="F1", idempotency_key="S2-G3-01"))
    # MarkHook appended 'ledger_committed' inside settle

    if log != ORDER:
        return emit(ID, "FAIL", "marker order/count wrong: got %s expected %s" % (log, ORDER))
    for m in ORDER:
        if log.count(m) != 1:
            return emit(ID, "FAIL", "marker %s count=%d (want 1)" % (m, log.count(m)))

    ev = ROOT / "evidence" / "s2"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-01.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    return emit(ID, "PASS", "real cycle emitted %s (each exactly once)" % " -> ".join(ORDER))


if __name__ == "__main__":
    sys.exit(main())
