"""C16-01: anomaly-zone as a legal settlement unit — SETTLED part (C25-style).

SPEC (config/settlement_units.json is the single structured source):
  - anomaly_zone is a legal unit; its manifest carries parent_instance_id;
    it must go through settle(); no double posting; code channel is opt-in (D15).
  - the exact boundary of the unit is NOT RATIFIED. This test asserts the
    settled contract and rejects a smuggled concrete boundary before ratification.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "C16-01"


def main():
    cfg = ROOT / "config" / "settlement_units.json"
    if not cfg.is_file():
        return emit(ID, "PENDING", "settlement_units.json missing; unit undefined")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    ratified = data.get("ratified", {})
    checks = {
        "unit_type": "anomaly_zone",
        "is_legal_settlement_unit": True,
        "manifest_parent_field": "parent_instance_id",
        "must_go_through_settle": True,
        "no_double_posting": True,
        "code_channel": "opt_in_only",
    }
    drift = ["%s=%r expected %r" % (k, ratified.get(k), v)
             for k, v in checks.items() if ratified.get(k) != v]
    if drift:
        return emit(ID, "FAIL", "settlement_units.json ratified drift: " + "; ".join(drift))

    unrat = data.get("unratified", {})
    if unrat.get("boundary_rules") != "UNRATIFIED":
        return emit(ID, "FAIL", "boundary_rules must remain UNRATIFIED")

    return emit(ID, "PASS", "settled unit contract OK; boundary left unratified (not invented)")


if __name__ == "__main__":
    sys.exit(main())
