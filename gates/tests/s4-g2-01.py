"""S4-G2-01: checklist items are all closed, no dangling checks (00 §7).

All 11 items have status defined or removed; no third value; defined items
carry an object definition. Structural contract only — judge=human items do
not require us to invent their (unratified) numeric ranges.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G2-01"


def main():
    cfg = ROOT / "config" / "checklist.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/checklist.json missing (P6 deliverable)")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if len(items) != 11:
        return emit(ID, "FAIL", "expected 11 checklist items, got %d" % len(items))

    enum = set(data.get("status_enum", ["defined", "removed"]))
    bad = []
    for it in items:
        status = it.get("status")
        if status not in enum:
            bad.append("id=%s status=%r not in %s" % (it.get("id"), status, sorted(enum)))
        elif status == "defined":
            if not isinstance(it.get("definition"), dict) or not it["definition"]:
                bad.append("id=%s defined without object definition" % it.get("id"))
        elif status == "removed" and not it.get("reason"):
            bad.append("id=%s removed without reason" % it.get("id"))
    if bad:
        return emit(ID, "FAIL", "checklist drift: " + "; ".join(bad))

    ids = [it["id"] for it in items]
    if len(set(ids)) != 11:
        return emit(ID, "FAIL", "checklist ids not unique")
    return emit(ID, "PASS", "11 items closed: %d defined / %d removed" % (
        sum(1 for it in items if it["status"] == "defined"),
        sum(1 for it in items if it["status"] == "removed")))


if __name__ == "__main__":
    sys.exit(main())
