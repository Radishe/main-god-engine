"""S2-G1-03: axis heterogeneity holds across F1 / F2 / D1.

D1's axis set must intersect F1 and F2, and add at least one axis neither has.
The engine never names these axes itself (I2) — they live only in instance data.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S2-G1-03"


def axes_of(iid):
    p = ROOT / "content" / "instances" / iid / "instance.json"
    if not p.is_file():
        return None
    return set(json.loads(p.read_text(encoding="utf-8")).get("axes", {}).keys())


def main():
    f1, f2, d1 = axes_of("F1"), axes_of("F2"), axes_of("D1")
    if not all((f1, f2, d1)):
        return emit(ID, "FAIL", "F1/F2/D1 instances not all present")
    if not (d1 & f1):
        return emit(ID, "FAIL", "D1 axes do not intersect F1")
    if not (d1 & f2):
        return emit(ID, "FAIL", "D1 axes do not intersect F2")
    unique = d1 - (f1 | f2)
    if not unique:
        return emit(ID, "FAIL", "D1 has no axis unique to itself")
    return emit(ID, "PASS", "D1 intersects F1=%s F2=%s, unique=%s" % (
        sorted(d1 & f1), sorted(d1 & f2), sorted(unique)))


if __name__ == "__main__":
    sys.exit(main())
