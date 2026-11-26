"""F6 malicious instance fixture (00 §1).

Fixed behaviour: on run(), attempt a direct write to the ledger's credits field.
This module is data/fixture, not part of the product engine. It is handed a
read-only ledger view by the engine; a direct write must be rejected.
"""

WRITE_TARGET = "credits"


def run(ledger_view):
    """Try to mutate the ledger directly. Return a marker describing the outcome."""
    try:
        ledger_view[WRITE_TARGET] = -999999
    except Exception as exc:  # the engine must reject this, not crash
        return {"instance": "F6", "direct_write": "blocked", "reason": type(exc).__name__}
    return {"instance": "F6", "direct_write": "succeeded", "reason": ""}
