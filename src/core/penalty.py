"""P1 penalty execution (C11).

D14: executor is the main-god engine, not the instance. The instance only
declares completion=failure. Deduction is simplified to credits only; no
attribute/item valuation, no permanent-item conflict, no demotion.

The engine computes the credit delta for a failure; the instance-supplied
credit_delta is NOT used as a deduction source for failures.
"""

import json
from pathlib import Path

from .ledger import Rejected

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT_ROOT / "config" / "penalty.json"


def load_rules():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def engine_completed_delta(manifest, volume=None):
    """Return the credit delta the engine applies for a non-success settlement.

    Only `completion=success` lets the instance's own credit_delta through (that
    is the legitimate产出 channel). Every other completion is computed here:

      * failure  -> deduct by task-volume anchor (D1 / D14, simplified credits-only)
      * aborted  -> 0 (D16: exit and settle, no extra asset deduction)

    The instance's credit_delta is NEVER a source of loss for either case.
    """
    rules = load_rules()
    if rules.get("executor") != "maingod_engine":
        raise Rejected("invalid_field:penalty_executor")

    completion = manifest.get("completion")
    if completion == "aborted":
        # D16: death = exit and settle as未完成; no revive, no extra asset loss.
        return 0
    if completion != "failure":
        # success is handled by the caller; unknown completions are rejected upstream
        return 0

    # failure: engine computes deduction from the task-volume anchor
    if volume is None:
        return 0  # no volume declared -> no deduction, never the instance's number
    if not isinstance(volume, int) or isinstance(volume, bool) or volume <= 0:
        raise Rejected("invalid_field:task_volume")
    if rules.get("deduction_chain") != "simplified" or rules.get("deduction_order") != ["credits"]:
        raise Rejected("invalid_field:deduction_chain")
    return -volume


# Backward-compatible alias for callers that used the earlier name.
failure_credit_delta = engine_completed_delta
