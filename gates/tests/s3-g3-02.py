"""S3-G3-02: main failure cannot be bypassed by side volume (00 §6 / D20).

config/scoring.json share_rules.main_fail_side_factor must be applied to the
SCORE side (not payout), and a main-failed case must yield <= the non-failed
case's rate. Driven by ratified D20 config; no invented cap.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit
sys.path.insert(0, str(ROOT))
from src.core.scoring import effective_score_and_rate

ID = "S3-G3-02"


def main():
    cfg = ROOT / "config" / "scoring.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "scoring.json missing")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    rules = data.get("share_rules", {})
    if rules.get("factor_applies_to") != "score":
        return emit(ID, "FAIL", "factor applies to %r (want score)" % rules.get("factor_applies_to"))
    factor = rules.get("main_fail_side_factor")
    if not isinstance(factor, (int, float)) or not 0 < factor <= 1:
        return emit(ID, "FAIL", "main_fail_side_factor invalid: %r" % factor)

    base = {"volume": 100, "score": 80, "main_share": 0.6, "side_share": 0.4,
            "main_failed": False, "event_flags": []}
    failed = dict(base, main_failed=True)
    s_ok, r_ok = effective_score_and_rate(base, data)
    s_fail, r_fail = effective_score_and_rate(failed, data)
    if r_fail > r_ok:
        return emit(ID, "FAIL", "main-failed rate %.3f > success %.3f" % (r_fail, r_ok))

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-02.json").write_text(json.dumps(
        {"factor": factor, "applies_to": "score", "rate_ok": r_ok, "rate_fail": r_fail},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "main-failed rate %.3f <= success %.3f (score-side factor)" % (r_fail, r_ok))


if __name__ == "__main__":
    sys.exit(main())
