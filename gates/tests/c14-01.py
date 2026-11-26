"""C14-01: exchange uses one unified numeric vocabulary (00 §12.2 / I5).

SPEC: every vocab entry has id/cost/effect/kind (+enabled_in per stub);
ids are globally unique; a manifest ID must hit the vocabulary; payout
magnitude matches the entry's cost; effects outside the vocabulary are refused.

COST IS A STRUCTURAL PLACEHOLDER: D20's 1:1 is the scoring exchange rate, not
an item price list. No concrete price table is invented here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.notary.exchange import (
    all_entries, exchange_entries, lookup, is_known_effect,
    payout_for, duplicate_ids, is_well_formed,
)

ID = "C14-01"


def main():
    if not (ROOT / "vocab" / "exchange.json").is_file():
        return emit(ID, "FAIL", "vocab/exchange.json missing; P4 not implemented")

    # 1. every entry well-formed per vocabulary stub
    entries = all_entries()
    if not entries:
        return emit(ID, "FAIL", "vocabulary empty")
    malformed = [e.get("id") for e in entries if not is_well_formed(e)]
    if malformed:
        return emit(ID, "FAIL", "malformed entries: " + ",".join(str(x) for x in malformed))

    # 2. ids globally unique across all sources
    dups = duplicate_ids()
    if dups:
        return emit(ID, "FAIL", "duplicate vocab ids: " + ",".join(dups))

    # 3. every exchange id hits the vocabulary; unknown ids miss
    ex = exchange_entries()
    if not ex:
        return emit(ID, "FAIL", "exchange vocabulary empty")
    for e in ex:
        if lookup(e["id"]) is None:
            return emit(ID, "FAIL", "exchange id not resolvable: " + e["id"])
    if lookup("__C14_UNKNOWN_ID__") is not None:
        return emit(ID, "FAIL", "unknown id wrongly resolved")

    # 4. payout magnitude == cost (direction is the settlement layer's job)
    for e in ex:
        if payout_for(e["id"]) != e["cost"]:
            return emit(ID, "FAIL", "payout != cost for " + e["id"])

    # 5. effects outside the vocabulary are rejected
    for e in ex:
        if not is_known_effect(e["effect"]):
            return emit(ID, "FAIL", "registered effect not known: " + e["effect"])
    if is_known_effect("__C14_FOREIGN_EFFECT__"):
        return emit(ID, "FAIL", "foreign effect accepted")

    return emit(ID, "PASS", "vocabulary well-formed: %d entries, %d exchange, ids unique, "
                "payout=cost, foreign effect rejected" % (len(entries), len(ex)))


if __name__ == "__main__":
    sys.exit(main())
