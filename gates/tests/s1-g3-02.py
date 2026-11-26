"""S1-G3-02: duplicate submission is deduplicated (00 §4).

The same idempotency_key submitted twice: the 2nd is rejected with
duplicate_settlement, credits increase exactly once, and the log names the code.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine, Rejected

ID = "S1-G3-02"


class LogHooks:
    def __init__(self):
        self.lines = []

    def reject(self, code, detail):
        self.lines.append("%s:%s" % (code, detail))

    def committed(self, instance_id, delta):
        self.lines.append("committed:%s:%d" % (instance_id, delta))


def main():
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    hooks = LogHooks()
    engine = Engine(ledger, hooks=hooks)
    manifest = dict(f4, idempotency_key="S1-G3-02-DUP")

    engine.settle(manifest)
    once = engine.ledger().as_dict()["credits"]
    err = ""
    try:
        engine.settle(manifest)
    except Rejected as exc:
        err = str(exc)
    twice = engine.ledger().as_dict()["credits"]

    if not err or "duplicate_settlement" not in err:
        return emit(ID, "FAIL", "duplicate not rejected with duplicate_settlement: %r" % err)
    if once != twice:
        return emit(ID, "FAIL", "credits changed on duplicate: %d -> %d" % (once, twice))
    if not any("duplicate_settlement" in l for l in hooks.lines):
        return emit(ID, "FAIL", "no duplicate_settlement log line")

    ev = ROOT / "evidence" / "s1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-02.log").write_text("\n".join(hooks.lines) + "\n", encoding="utf-8")
    return emit(ID, "PASS", "2nd submit rejected; credits=%d (one increase); log ok" % once)


if __name__ == "__main__":
    sys.exit(main())
