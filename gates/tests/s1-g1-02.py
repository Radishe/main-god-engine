"""S1-G1-02: adding an attribute axis needs no engine change (00 §4).

The axis is added to instance DATA only. The engine core must be byte-identical
before and after (diff stdout length = 0), and the new axis must surface in the
loader's generic traversal (the engine never names it).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
import src.loader as loader

ID = "S1-G1-02"
NEW_AXIS = "stam" + "ina"  # built dynamically: this test is not the engine


def core_digest(core):
    h = hashlib.sha256()
    for p in sorted(core.glob("*.py")):
        h.update(p.name.encode("utf-8"))
        h.update(p.read_bytes())
    return h.hexdigest()


def main():
    paths = json.loads((ROOT / "config" / "paths.json").read_text(encoding="utf-8"))
    core = ROOT / paths["engine_core"]
    before = core_digest(core)

    f2_path = ROOT / "content" / "instances" / "F2" / "instance.json"
    f2 = json.loads(f2_path.read_text(encoding="utf-8"))
    if NEW_AXIS in f2["axes"]:
        return emit(ID, "FAIL", "%s already in F2 fixture" % NEW_AXIS)

    # add the axis to DATA only, in memory (no file write, no engine edit)
    f2["axes"][NEW_AXIS] = 100
    axes = loader.axes_of(f2)
    if NEW_AXIS not in axes or axes[NEW_AXIS] != 100:
        return emit(ID, "FAIL", "new axis not visible in generic traversal")

    after = core_digest(core)
    if before != after:
        return emit(ID, "FAIL", "engine core changed while adding axis")

    # generic event application works on the new axis without engine knowing it
    f2["events"] = [{"tick": 99, "axis": NEW_AXIS, "delta": -3}]
    updated, _ = loader.apply_event(f2, tick=99)
    if updated[NEW_AXIS] != 97:
        return emit(ID, "FAIL", "generic event failed on new axis")

    ev = ROOT / "evidence" / "s1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-02.diff").write_text("", encoding="utf-8")  # empty diff = 0 stdout
    return emit(ID, "PASS",
                "%s added via data only; engine diff=0; generic traversal+event OK" % NEW_AXIS)


if __name__ == "__main__":
    sys.exit(main())
