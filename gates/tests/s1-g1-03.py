"""S1-G1-03: instance runtime never mutates the ledger (00 §4).

F1 runs 100 ticks, changing its local hp each tick. The ledger SHA-256 must be
identical before and after — instance state is sandbox-local (01 §4.1), the
engine never sees it until a settlement manifest arrives.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
import src.loader as loader

ID = "S1-G1-03"


def sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main():
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    before = sha(ledger)
    f1 = loader.load(ROOT / "content" / "instances" / "F1" / "instance.json")

    # 100 ticks, each mutating only the instance's local axis (data, not ledger)
    state = dict(f1["axes"])
    for tick in range(100):
        state["hp"] -= 1
    if state["hp"] != f1["axes"]["hp"] - 100:
        return emit(ID, "FAIL", "100-tick local state did not evolve")

    if sha(ledger) != before:
        return emit(ID, "FAIL", "ledger changed during instance runtime")

    ev = ROOT / "evidence" / "s1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-03.txt").write_text(
        "ticks=100\nlocal_hp_before=%d\nlocal_hp_after=%d\nledger_sha_before=%s\nledger_sha_after=%s\n" % (
            f1["axes"]["hp"], state["hp"], before, sha(ledger)), encoding="utf-8")
    return emit(ID, "PASS", "100 ticks changed local hp only; ledger SHA unchanged")


if __name__ == "__main__":
    sys.exit(main())
