"""C16-01: anomaly-zone settlement boundary (01 §扭曲节点 / 04 §5 / D15 / C16).

Unit contract: anomaly_zone is legal, manifest carries parent_instance_id,
must go through settle(), no double posting, code channel opt-in.

Boundary RATIFIED as structural constraints: a declarative zone is legal iff
it satisfies the three structural requirements (NOT author declaration alone);
human review applies only to the DLL code channel. An implementation that
relaxes this to 'author declares = legal' is rejected.
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

    b = data.get("boundary_rules", {})
    if b.get("status") != "RATIFIED":
        return emit(ID, "FAIL", "boundary_rules not RATIFIED")
    dec = b.get("declarative_channel", {})
    if dec.get("author_declaration_alone_sufficient") is not False:
        return emit(ID, "FAIL", "author declaration alone accepted as boundary")
    req = set(dec.get("requires", []))
    want = {"must_go_through_settle", "parent_instance_id", "no_double_posting"}
    if not want.issubset(req):
        return emit(ID, "FAIL", "structural requirements missing: %s" % sorted(want - req))
    dll = b.get("dll_channel", {})
    if dll.get("requires_human_review") is not True:
        return emit(ID, "FAIL", "DLL channel must require human review (D15)")

    return emit(ID, "PASS", "boundary = 3 structural constraints (not author fiat); "
                "human review only for DLL channel")


if __name__ == "__main__":
    sys.exit(main())
