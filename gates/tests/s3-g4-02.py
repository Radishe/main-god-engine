"""S3-G4-02: permanent-item conflict is settled (00 §6 / D14).

D14 closed the A→B→C deduction chain; config/penalty.json records
permanent_item_conflict=not_applicable. The test verifies that the conflict
is explicitly retired — NOT that a (now-abolished) deduction comparison runs.
This avoids resurrecting a mechanism D14 deliberately removed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S3-G4-02"


def main():
    cfg = ROOT / "config" / "penalty.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/penalty.json missing")
    d = json.loads(cfg.read_text(encoding="utf-8"))
    if d.get("permanent_item_conflict") != "not_applicable":
        return emit(ID, "FAIL", "permanent conflict=%r (want not_applicable / D14)" %
                    d.get("permanent_item_conflict"))
    if d.get("attribute_valuation_required") is not False:
        return emit(ID, "FAIL", "attribute valuation re-enabled (D14 deprecated)")

    dec = ROOT / "docs" / "设计决议记录.md"
    text = dec.read_text(encoding="utf-8") if dec.is_file() else ""
    import re
    m = re.search(r"^## D14\b.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m or "A1" not in m.group(1):
        return emit(ID, "FAIL", "D14 permanent conflict retirement not backfilled")

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g4-02.json").write_text(json.dumps(
        {"permanent_item_conflict": "not_applicable",
         "attribute_valuation_required": False, "decision": "D14"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "permanent conflict explicitly retired by D14 (not fabricated)")


if __name__ == "__main__":
    sys.exit(main())
