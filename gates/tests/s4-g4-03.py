"""S4-G4-03: demo instance scale — at least 3, axes not all identical,
at least 2 render_profile values (D17: metadata placeholder only).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G4-03"


def main():
    base = ROOT / "content" / "instances"
    paths = sorted(base.glob("*/instance.json")) if base.is_dir() else []
    if len(paths) < 3:
        return emit(ID, "FAIL", "need >=3 instances, got %d" % len(paths))
    axis_sets, profiles = [], set()
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        axis_sets.append(frozenset(data.get("axes", {}).keys()))
        if data.get("render_profile"):
            profiles.add(data["render_profile"])
    if len(set(axis_sets)) < 2:
        return emit(ID, "FAIL", "all instances share the same axis set")
    if len(profiles) < 2:
        return emit(ID, "FAIL", "need >=2 render_profile values")
    return emit(ID, "PASS", "%d instances, %d distinct axis sets, profiles=%s" % (
        len(paths), len(set(axis_sets)), sorted(profiles)))


if __name__ == "__main__":
    sys.exit(main())
