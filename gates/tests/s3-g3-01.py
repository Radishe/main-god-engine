"""S3-G3-01: mainline failure weighting has exactly one interpretation (D20).

Four cases (mainline success/failure x side full/partial) each yield a definite
rate. The D8 factor applies on the SCORE side only (config share_rules.
factor_applies_to == 'score'); no separate grade cap is applied.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.scoring import load_config, effective_score_and_rate

ID = "S3-G3-01"


def main():
    cfg = load_config()
    if cfg["share_rules"].get("factor_applies_to") != "score":
        return emit(ID, "FAIL", "D8 factor is not applied on the score side")
    if cfg["share_rules"].get("main_fail_grade_cap") is not None:
        return emit(ID, "FAIL", "a separate grade cap exists; D20 says no cap")

    # volume 100, main_share 0.6 / side_share 0.4 (>=50% floor)
    def claims(main_failed, side_full):
        return {"schema_version": 1, "score": 100, "volume": 100,
                "main_share": 0.6, "side_share": 0.4,
                "main_failed": main_failed,
                "event_flags": ["side_full"] if side_full else []}

    results = {}
    for mf in (False, True):
        for sf in (False, True):
            eff, rate = effective_score_and_rate(claims(mf, sf), cfg)
            results[(mf, sf)] = round(rate, 6)

    # main success: side contributes at full weight regardless of side_full flag
    # (score is a single aggregate; side_full is metadata, not a second number)
    if results[(False, False)] != results[(False, True)]:
        return emit(ID, "FAIL", "side_full changed rate when main succeeded")
    # main failure: side share is halved -> rate drops by main-independent side part
    ok_rate = results[(False, True)]
    fail_rate = results[(True, True)]
    if not 0 <= fail_rate < ok_rate:
        return emit(ID, "FAIL", "main failure did not lower rate deterministically")
    # D8 factor is 0.5 on side (0.4 share): 0.6 + 0.4*0.5 = 0.8
    if abs(fail_rate - 0.8) > 1e-9:
        return emit(ID, "FAIL", "main-failure rate %s != 0.8" % fail_rate)
    return emit(ID, "PASS", "four cases deterministic; score-side factor; rates=%s" % results)


if __name__ == "__main__":
    sys.exit(main())
