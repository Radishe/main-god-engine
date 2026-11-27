"""S0-G2-01: settlement field table is final and mirrors the frozen stub (00 §3).

Config/settlement.json must exist, declare all 8 fields (6 required + 2
optional after D18) with per-field type and required/optional ownership, and
match the stub's field set exactly. This is a real cross-file drift check.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S0-G2-01"


def main():
    cfg = ROOT / "config" / "settlement.json"
    stub = ROOT / "gates" / "stubs" / "settlement.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/settlement.json missing (field table not finalised)")
    if not stub.is_file():
        return emit(ID, "FAIL", "settlement stub missing")

    data = json.loads(cfg.read_text(encoding="utf-8"))
    fields = data.get("fields", {})
    sm = json.loads(stub.read_text(encoding="utf-8"))["settlement_manifest"]
    expected = set(sm["required"]) | set(sm.get("optional", []))
    if len(expected) != 8:
        return emit(ID, "FAIL", "stub field set not 8 (D18): %s" % sorted(expected))
    if set(fields) != expected:
        return emit(ID, "FAIL", "config/stub field drift: config=%s stub=%s" % (
            sorted(fields), sorted(expected)))

    for name, spec in fields.items():
        if "type" not in spec or "required" not in spec:
            return emit(ID, "FAIL", "%s lacks type/required declaration" % name)
        want_required = name in sm["required"]
        if spec["required"] != want_required:
            return emit(ID, "FAIL", "%s required=%r expected %r" % (
                name, spec["required"], want_required))

    ev = ROOT / "evidence" / "s0"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g2-01.json").write_text(json.dumps(
        {"fields": sorted(fields), "count": len(fields), "matches_stub": True},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "field table final: 8 fields, type+ownership declared, matches stub")


if __name__ == "__main__":
    sys.exit(main())
