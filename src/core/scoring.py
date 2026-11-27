"""D12 scoring chain, D20-ratified values. score -> rate -> grade -> coefficient -> payout.

Every number comes from config/scoring.json (ratified in D20). This module
contains NO invented values, NO identity placeholders, and NO concrete instance
axis-name literals (I2 static scan) — axis names are read from config's
engine_must_not_read list only to reject them, never hardcoded here.

The chain:
  rate    = (main_score + side_score * factor) / volume
  grade   = first band whose min_rate <= rate  (F handled as a failure state)
  payout  = volume * tier_coefficient * grade_coefficient * exchange_rate
  delta   = payout  (the ledger adds this to credits)
"""

import json
from pathlib import Path

from .ledger import Rejected

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT_ROOT / "config" / "scoring.json"
TIERS = PROJECT_ROOT / "config" / "tiers.json"


def tier_coefficient(tier):
    """D21: coefficient(n) = 2^(n-1), read from the shared tier config."""
    if not TIERS.is_file():
        raise Rejected("invalid_field:tier_config_missing")
    data = json.loads(TIERS.read_text(encoding="utf-8"))
    if tier == 0:
        return data["novice"]["coefficient"]
    for t in data["tiers"]:
        if t["tier"] == tier:
            return t["coefficient"]
    raise Rejected("invalid_field:tier_out_of_range")


def load_config():
    if not CONFIG.is_file():
        raise Rejected("rejected_unratified_scoring:config_missing")
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def is_enabled():
    """Whether the scoring chain is formally enabled (values ratified)."""
    if not CONFIG.is_file():
        return False
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except ValueError:
        return False
    return data.get("enabled") is True and data.get("status") != "UNRATIFIED"


def decode_claims(manifest):
    """Return structured claims dict from a manifest's claims field, or None."""
    raw = manifest.get("claims")
    if raw is None:
        return None
    return json.loads(raw) if isinstance(raw, str) else raw


def validate_shares(claims, cfg):
    """D20: shares sum to 100% and main share has a floor.

    Public since D25: the CLI contract layer calls this same function so the
    rule has one implementation and one config truth-source (config/scoring.json).
    """
    rules = cfg["share_rules"]
    main, side = claims.get("main_share"), claims.get("side_share")
    if not isinstance(main, (int, float)) or not isinstance(side, (int, float)):
        raise Rejected("invalid_field:claims:share_type")
    if rules.get("must_sum_to_100"):
        if abs((main + side) - 1.0) > 1e-9:
            raise Rejected("invalid_field:claims:share_sum")
    floor = rules.get("main_min_share")
    if floor is not None and main < floor:
        raise Rejected("invalid_field:claims:main_share_below_min")


def grade_for(rate, cfg):
    """First band (descending) whose min_rate <= rate; F if below all."""
    bands = sorted(cfg["grade_bands"], key=lambda b: b["min_rate"], reverse=True)
    for band in bands:
        if rate >= band["min_rate"]:
            return band["grade"]
    return cfg.get("failure_grade", "F")


def effective_score_and_rate(claims, cfg=None):
    """D12/D8: apply the main-failure factor on the SCORE side, return (score, rate).

    Exposed so S3-G3-01 can assert the four main/side combinations deterministically.
    """
    cfg = cfg if cfg is not None else load_config()
    validate_shares(claims, cfg)
    volume, score = claims.get("volume"), claims.get("score")
    if not isinstance(volume, int) or isinstance(volume, bool) or volume <= 0:
        raise Rejected("invalid_field:claims:volume")
    if not isinstance(score, int) or isinstance(score, bool) or score < 0:
        raise Rejected("invalid_field:claims:score")
    main_failed = claims.get("main_failed")
    if not isinstance(main_failed, bool):
        raise Rejected("invalid_field:claims:main_failed")
    rules = cfg["share_rules"]
    factor = rules["main_fail_side_factor"] if main_failed else 1.0
    effective = claims["main_share"] * score + claims["side_share"] * score * factor
    return effective, effective / volume


def compute_payout(claims, ledger_credits=None, tier_coefficient=1.0):
    """Return the credit delta from D20-ratified structured evidence."""
    cfg = load_config()
    if not is_enabled():
        raise Rejected("rejected_unratified_scoring:values_not_ratified")

    effective, rate = effective_score_and_rate(claims, cfg)
    grade = grade_for(rate, cfg)
    if grade == cfg.get("failure_grade", "F"):
        # F is a failure state, handled by D14 penalty — not a payout coefficient.
        return 0
    coeff = cfg["coefficients"][grade]
    payout_cfg = cfg["payout"]
    volume = claims["volume"]  # D20: base output = volume
    payout = volume * tier_coefficient * coeff * payout_cfg["exchange_rate"]
    # credits must be integral; round half-up deterministically
    return int(payout + 0.5)
