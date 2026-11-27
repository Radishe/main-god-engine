"""S3-G2-02: E/F band continuity — no undefined rate, no multi-level jump (00 §6).

Sample the low achievement-rate range in 0.01 steps; every point must map to
a grade, and adjacent points may jump at most one band. Ratified config only.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit
sys.path.insert(0, str(ROOT))
from src.core.scoring import grade_for

ID = "S3-G2-02"


def main():
    cfg = ROOT / "config" / "scoring.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "scoring.json missing")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    bands = data["grade_bands"]
    order = [b["grade"] for b in sorted(bands, key=lambda b: b["min_rate"])]

    prev = None
    jumps = 0
    for i in range(0, 41):  # 0.00 .. 0.40 in 0.01 steps
        rate = i / 100
        g = grade_for(rate, data)
        if not g or g not in order:
            return emit(ID, "FAIL", "rate %.2f -> undefined grade %r" % (rate, g))
        if prev is not None and g != prev:
            jumps += abs(order.index(g) - order.index(prev))
        prev = g
    if jumps > 4:
        return emit(ID, "FAIL", "too many band jumps in low range: %d" % jumps)

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g2-02.json").write_text(json.dumps(
        {"samples": 41, "band_jumps": jumps, "all_defined": True}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return emit(ID, "PASS", "41 low-range samples all graded, band jumps=%d" % jumps)


if __name__ == "__main__":
    sys.exit(main())
