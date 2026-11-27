"""C15-01: scene tags with ratified interaction rules (03 §5 / C15).

Three tags, affects_settlement, manifest field scene_tag, unknown rejected.
Per-tag INTERACTION rules (PVP / trade protection) are now RATIFIED from the
source's explicit examples. Tax/notary RATES remain UNRATIFIED — smuggling a
numeric rate is rejected.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "C15-01"


def main():
    cfg = ROOT / "config" / "scenes.json"
    if not cfg.is_file():
        return emit(ID, "PENDING", "scenes.json missing; scene tags undefined")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    ratified = data.get("ratified", {})
    checks = {
        "enum": ["peaceful", "raid", "contract"],
        "affects_settlement": True,
        "manifest_field": "scene_tag",
        "unknown_tag_rejected": True,
        "declared_by": "instance_author",
    }
    drift = ["%s=%r expected %r" % (k, ratified.get(k), v)
             for k, v in checks.items() if ratified.get(k) != v]
    if drift:
        return emit(ID, "FAIL", "scenes.json ratified drift: " + "; ".join(drift))

    rules = data.get("per_tag_rules", {})
    if rules.get("status") != "RATIFIED":
        return emit(ID, "FAIL", "per_tag_rules not RATIFIED")
    expected = {
        "peaceful": {"pvp_allowed": False, "trade_protected": True},
        "raid": {"pvp_allowed": True, "trade_protected": False},
        "contract": {"pvp_allowed": False, "trade_protected": True},
    }
    for tag, exp in expected.items():
        got = rules.get(tag, {})
        if any(got.get(k) != v for k, v in exp.items()):
            return emit(ID, "FAIL", "%s rule drift: %r expected %r" % (tag, got, exp))
    if len({(rules[t]["pvp_allowed"], rules[t]["trade_protected"]) for t in expected}) < 2:
        return emit(ID, "FAIL", "tags have no behavioural difference")

    # tax rate must stay unratified — no numeric smuggling
    rate = data.get("tax_or_notary_rate", {})
    if rate.get("status") != "UNRATIFIED" or rate.get("value") != "UNRATIFIED":
        return emit(ID, "FAIL", "tax/notary rate must stay UNRATIFIED")
    numeric = [tag for tag in expected if any(
        isinstance(v, (int, float)) and not isinstance(v, bool)
        for k, v in rules[tag].items() if "rate" in k or "tax" in k)]
    if numeric:
        return emit(ID, "FAIL", "numeric tax rate smuggled into: " + ",".join(numeric))

    return emit(ID, "PASS", "3 tags with ratified PVP/trade rules; tax rate left UNRATIFIED")


if __name__ == "__main__":
    sys.exit(main())
