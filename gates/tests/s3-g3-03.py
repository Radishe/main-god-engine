"""S3-G3-03: share table must satisfy ratified constraints (00 §6 / D20).

config/scoring.json share_rules: shares sum to 100, main >= min. Invalid
shares are rejected by the real scoring validator. No new constraint invented.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit
sys.path.insert(0, str(ROOT))
from src.core.scoring import effective_score_and_rate
from src.core.ledger import Rejected

ID = "S3-G3-03"


def main():
    cfg = ROOT / "config" / "scoring.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "scoring.json missing")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    rules = data.get("share_rules", {})
    if rules.get("must_sum_to_100") is not True:
        return emit(ID, "FAIL", "shares must sum to 100 not set")
    minimum = rules.get("main_min_share")
    if not isinstance(minimum, (int, float)):
        return emit(ID, "FAIL", "main_min_share invalid")

    # legal share table passes
    legal = {"volume": 100, "score": 80, "main_share": 0.6, "side_share": 0.4,
             "main_failed": False, "event_flags": []}
    effective_score_and_rate(legal, data)  # raises if invalid

    # illegal: shares do not sum to 100
    bad = dict(legal, main_share=0.7, side_share=0.4)
    rejected = False
    try:
        effective_score_and_rate(bad, data)
    except Rejected:
        rejected = True
    if not rejected:
        return emit(ID, "FAIL", "share table not summing to 100 was accepted")

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-03.log").write_text(
        "legal shares accepted; 0.7+0.4=1.1 rejected; main_min_share=%s\n" % minimum, encoding="utf-8")
    return emit(ID, "PASS", "share constraints enforced: legal passes, 110%% sum rejected")


if __name__ == "__main__":
    sys.exit(main())
