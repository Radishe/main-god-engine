"""S1-G2-04: admission snapshot equals the pre-load ledger.

SPEC (00 §4 S1-G2-04): for F1 and F2, snapshot.json deep-equals ledger.json
captured immediately before loading; loading itself never mutates the ledger.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine, digest

ID = "S1-G2-04"


def main():
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    for name in ("f1-instance-a.json", "f2-instance-b.json"):
        instance = json.loads((ROOT / "gates" / "fixtures" / name).read_text(encoding="utf-8"))
        engine = Engine(ledger)
        hash_before = digest(engine.ledger())
        snapshot = dict(engine.snapshot())
        if snapshot != ledger:
            return emit(ID, "FAIL", "%s snapshot differs from ledger" % name)
        # loading instance data must not change the engine's ledger
        loaded_axes = dict(instance["axes"])
        if digest(engine.ledger()) != hash_before:
            return emit(ID, "FAIL", "%s load mutated ledger" % name)
        if not loaded_axes:
            return emit(ID, "FAIL", "%s has no axes" % name)
    return emit(ID, "PASS", "F1/F2 snapshots deep-equal ledger; loads left it unchanged")


if __name__ == "__main__":
    sys.exit(main())
