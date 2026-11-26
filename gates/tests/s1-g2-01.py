"""S1-G2-01: a malicious instance cannot write the ledger.

SPEC (00 §4 S1-G2-01): load F6, run it once; process exit = 0, ledger SHA-256
unchanged, and a rejection log line contains rejected_direct_write.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine, Rejected, digest

ID = "S1-G2-01"


class LogHooks:
    def __init__(self):
        self.lines = []

    def reject(self, code, detail):
        self.lines.append("%s:%s" % (code, detail))

    def committed(self, instance_id, delta):
        self.lines.append("committed:%s:%d" % (instance_id, delta))


def main():
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    hooks = LogHooks()
    engine = Engine(ledger, hooks=hooks)
    before = digest(engine.ledger())

    spec = importlib.util.spec_from_file_location("f6", ROOT / "gates" / "fixtures" / "f6-malicious.py")
    f6 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(f6)
    view = engine.ledger()
    outcome = f6.run(view)

    # Audit P1-2: nested containers and private attributes must not be writable.
    probes = []
    try:
        view["ability_ids"].append("stolen")
        probes.append("nested-write-not-blocked")
    except (AttributeError, Rejected):
        pass
    for attr in ("_data", "_hooks"):
        try:
            getattr(view, attr)
            probes.append("private-%s-exposed" % attr)
        except AttributeError:
            pass

    after = digest(engine.ledger())
    if outcome.get("direct_write") != "blocked":
        return emit(ID, "FAIL", "F6 direct write was not blocked: %r" % outcome)
    if probes:
        return emit(ID, "FAIL", "frozen view loopholes: " + ",".join(probes))
    if before != after:
        return emit(ID, "FAIL", "ledger hash changed: %s -> %s" % (before, after))
    if not any("rejected_direct_write" in line for line in hooks.lines):
        return emit(ID, "FAIL", "no rejected_direct_write log line")
    return emit(ID, "PASS", "hash unchanged; nested/private writes blocked; log=%s" % ";".join(hooks.lines))


if __name__ == "__main__":
    sys.exit(main())
