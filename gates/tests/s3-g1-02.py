"""S3-G1-02: tier table is internally consistent with its growth model (00 §6).

config/tiers.json declares growth_model=doubling; recompute each tier's
band_low from base_low and compare to the file. Pure mechanical check of a
ratified table (D21) — no new numbers are invented.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S3-G1-02"


def main():
    cfg = ROOT / "config" / "tiers.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/tiers.json missing")
    d = json.loads(cfg.read_text(encoding="utf-8"))
    model = d.get("growth_model")
    base = d.get("base_low")
    tiers = d.get("tiers", [])
    if model != "doubling" or not isinstance(base, int) or len(tiers) != 10:
        return emit(ID, "FAIL", "tiers shape drift: model=%r base=%r n=%d" % (
            model, base, len(tiers)))
    problems = []
    for t in tiers:
        tier, low, high = t.get("tier"), t.get("band_low"), t.get("band_high")
        want = base * (2 ** (tier - 1))
        if low != want:
            problems.append("tier %d band_low=%s expected %d" % (tier, low, want))
        if high != want * 2 - 1:
            problems.append("tier %d band_high=%s expected %d" % (tier, high, want * 2 - 1))
    if problems:
        return emit(ID, "FAIL", "; ".join(problems))

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-02.json").write_text(json.dumps(
        {"model": model, "base_low": base, "tiers": len(tiers), "recompute": "all_equal"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "10 tiers recompute exactly under doubling model")


if __name__ == "__main__":
    sys.exit(main())
