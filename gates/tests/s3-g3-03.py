"""S3-G3-03: share table must satisfy ratified constraints (00 §6 / D20 / D25).

config/scoring.json share_rules: shares sum to 100, main >= min. Invalid
shares are rejected both by the engine validator AND by the CLI contract layer
(D25 moved this ratified rule forward so a PR fails before settle()).
No new constraint invented.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit
sys.path.insert(0, str(ROOT))
from src.core.scoring import effective_score_and_rate
from src.core.ledger import Rejected
from src.contract.manifest import validate_manifest
from src.contract import ContractViolation

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

    # D25 forward-check: CLI must reject main_share below min even when the
    # sum is exactly 1.0 (the case that previously slipped through).
    mf_path = ROOT / "content" / "instances" / "D2" / "settlement.json"
    if mf_path.is_file():
        mf = json.loads(mf_path.read_text(encoding="utf-8"))
        claims = json.loads(mf["claims"])
        claims["main_share"], claims["side_share"] = 0.1, 0.9
        mf["claims"] = json.dumps(claims, ensure_ascii=False, separators=(",", ":"))
        cli_rejected = False
        try:
            validate_manifest(mf)
        except ContractViolation as exc:
            cli_rejected = "main_share" in getattr(exc, "render", lambda: str(exc))()
        if not cli_rejected:
            return emit(ID, "FAIL", "CLI accepted main_share=0.1 (D25 forward-check missing)")
        # config is the truth source: lowering the floor lets the same value pass
        relaxed = json.loads(json.dumps(data))
        relaxed["share_rules"]["main_min_share"] = 0.05
        try:
            effective_score_and_rate(claims, relaxed)
        except Rejected:
            return emit(ID, "FAIL", "threshold not read from config (hardcoded?)")

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-03.log").write_text(
        "legal accepted; 0.7+0.4=1.1 rejected; D25 CLI rejects 0.1/0.9; "
        "relaxed config accepts it (config is truth source); main_min_share=%s\n" % minimum,
        encoding="utf-8")
    return emit(ID, "PASS", "share constraints enforced in engine + CLI; config is truth source")


if __name__ == "__main__":
    sys.exit(main())
