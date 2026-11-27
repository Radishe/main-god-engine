"""C25-01: erasure semantics + the ratified memorial marker (D16/T2/C25).

SPEC (config/states.json is the single structured source of truth):
  - D16 death flow, T2 global-cumulative 3-strike counting;
  - peak_tier is engine-recorded via settle(), display-only, no setter,
    NOT in the settlement manifest and NOT in the ledger field set.

A pure '曾到达 X 阶' badge. An implementation that smuggles it into the
settlement manifest, the ledger fields, or makes it externally assignable is
rejected — those are the boundaries the maintainer ratified.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine, Rejected

ID = "C25-01"


def main():
    cfg = ROOT / "config" / "states.json"
    if not cfg.is_file():
        return emit(ID, "PENDING", "states.json missing; death vs erasure undefined")
    rules = json.loads(cfg.read_text(encoding="utf-8"))

    checks = {
        "death_flow": "exit_and_settle",
        "counts_toward_erasure": True,
        "erasure_count_scope": "global_cumulative",
        "erasure_count_threshold": 3,
        "erasure_count_reset_on_tier_change": False,
        "revive": False,
        "lethal_requires_declaration": True,
        "erasure_state": "registered",
        "non_erasure_state": "distinguishable",
    }
    drift = ["%s=%r expected %r" % (k, rules.get(k), v)
             for k, v in checks.items() if rules.get(k) != v]
    if drift:
        return emit(ID, "FAIL", "states.json drift: " + "; ".join(drift))

    mm = rules.get("memorial_marker", {})
    mm_checks = {
        "status": "RATIFIED", "field": "peak_tier",
        "source": "engine_recorded_only", "write_via": "Engine.settle()",
        "external_assignment": "forbidden", "display_only": True,
        "affects_settlement": False, "in_settlement_manifest": False,
        "in_ledger_fields": False,
    }
    mm_drift = ["%s=%r expected %r" % (k, mm.get(k), v)
                for k, v in mm_checks.items() if mm.get(k) != v]
    if mm_drift:
        return emit(ID, "FAIL", "memorial contract drift: " + "; ".join(mm_drift))

    # manifest field set must NOT include the memorial/count fields
    stub = json.loads((ROOT / "gates" / "stubs" / "settlement.json").read_text(encoding="utf-8"))
    fields = set(stub["settlement_manifest"]["required"]) | set(stub["settlement_manifest"].get("optional", []))
    if "peak_tier" in fields or "fail_count" in fields:
        return emit(ID, "FAIL", "memorial/count fields leaked into settlement manifest")

    # runtime: engine-only peak recording, read-only, idempotency preserved
    base = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    eng = Engine(base)
    if eng.peak_tier != 0:
        return emit(ID, "FAIL", "initial peak_tier != 0")
    eng.settle(dict(f4, idempotency_key="C25-HI"), tier=3)
    eng.settle(dict(f4, idempotency_key="C25-LO"), tier=1)
    if eng.peak_tier != 3:
        return emit(ID, "FAIL", "peak_tier not max-only: %r" % eng.peak_tier)
    try:
        eng.peak_tier = 9
        return emit(ID, "FAIL", "peak_tier externally assignable")
    except AttributeError:
        pass
    try:
        eng.settle(dict(f4, idempotency_key="C25-HI"), tier=5)
        return emit(ID, "FAIL", "idempotency lost on repeated key")
    except Rejected:
        if eng.peak_tier != 3:
            return emit(ID, "FAIL", "peak_tier changed on rejected settlement")
    if "peak_tier" in eng.ledger().as_dict():
        return emit(ID, "FAIL", "peak_tier leaked into ledger fields")

    return emit(ID, "PASS", "D16/T2 settled; peak_tier engine-only badge (3), "
                "not in manifest/ledger, idempotency preserved")


if __name__ == "__main__":
    sys.exit(main())
