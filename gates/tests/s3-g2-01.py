"""S3-G2-01: every achievement rate maps to exactly one grade (D20 bands).

Inputs: 0, each band lower bound, bound-1, 1.0, >1.0. Each returns a grade,
no empty return, >1.0 clamps to top grade.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.scoring import grade_for, load_config

ID = "S3-G2-01"


def main():
    cfg = load_config()
    bands = sorted(cfg["grade_bands"], key=lambda b: b["min_rate"])
    probes = [0.0, 1.0]
    for b in bands:
        probes.append(b["min_rate"])
        if b["min_rate"] > 0:
            probes.append(b["min_rate"] - 0.01)
    probes.append(1.5)  # >1.0 must clamp to top

    for rate in probes:
        grade = grade_for(rate, cfg)
        if not grade:
            return emit(ID, "FAIL", "empty grade for rate %s" % rate)
        if rate > 1.0 and grade != bands[-1]["grade"]:
            return emit(ID, "FAIL", "rate %s not clamped to top grade" % rate)

    grades = [b["grade"] for b in bands]
    if len(set(grades)) != len(grades):
        return emit(ID, "FAIL", "duplicate grades in bands")
    return emit(ID, "PASS", "%d rates probed, all mapped, >1.0 clamps to %s" % (
        len(probes), bands[-1]["grade"]))


if __name__ == "__main__":
    sys.exit(main())
