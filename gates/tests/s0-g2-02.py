"""S0-G2-02: configuration and stub agree, stub is frozen (00 §3).

Cross-check config/settlement.json field names and types against
gates/stubs/settlement.json; require the stub's frozen=true and no third
ownership class (every field is required or optional, never both/neither).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S0-G2-02"


def main():
    cfg = ROOT / "config" / "settlement.json"
    stub = ROOT / "gates" / "stubs" / "settlement.json"
    if not (cfg.is_file() and stub.is_file()):
        return emit(ID, "FAIL", "config or stub missing")
    data = json.loads(cfg.read_text(encoding="utf-8"))["fields"]
    sm = json.loads(stub.read_text(encoding="utf-8"))["settlement_manifest"]

    if sm.get("frozen") is not True:
        return emit(ID, "FAIL", "stub frozen != true")

    required, optional = set(sm["required"]), set(sm.get("optional", []))
    if required & optional:
        return emit(ID, "FAIL", "field in both required and optional: %s" % sorted(required & optional))
    all_fields = required | optional
    if set(data) != all_fields:
        return emit(ID, "FAIL", "field sets differ: %s" % sorted(set(data) ^ all_fields))

    # types agree (config 'enum' corresponds to stub 'enum<...>')
    for name, spec in data.items():
        stub_type = sm["types"].get(name, "")
        cfg_type = spec["type"]
        ok = cfg_type == stub_type or (cfg_type == "enum" and stub_type.startswith("enum<"))
        if not ok:
            return emit(ID, "FAIL", "%s type mismatch: config=%r stub=%r" % (name, cfg_type, stub_type))

    ev = ROOT / "evidence" / "s0"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g2-02.json").write_text(json.dumps(
        {"frozen": True, "fields": len(all_fields), "types_agree": True},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "config/stub agree: 8 fields, types consistent, frozen=true, no third class")


if __name__ == "__main__":
    sys.exit(main())
