"""C15-01: scene-tag differential settlement — SETTLED part only (C25-style).

SPEC (config/scenes.json is the single structured source of truth):
  - three tag names, affects_settlement, manifest field scene_tag,
    unknown tag rejected, declared by instance author — all SETTLED (03 §5).
  - the concrete notary/tax rule PER TAG is NOT RATIFIED. This test asserts the
    settled structure and rejects an implementation that smuggles concrete
    per-tag numbers into the ratified block before ratification.
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

    # unratified per-tag rules must stay explicitly unratified — no smuggling
    unrat = data.get("unratified", {})
    if unrat.get("per_tag_rules") != "UNRATIFIED":
        return emit(ID, "FAIL", "per_tag_rules must remain UNRATIFIED")
    # bool is a subclass of int in Python — exclude it so legitimate boolean
    # flags (affects_settlement / unknown_tag_rejected) are not mistaken for
    # smuggled concrete tax numbers.
    if any(isinstance(v, (int, float)) and not isinstance(v, bool)
           for v in ratified.values()):
        return emit(ID, "FAIL", "concrete numeric rule in ratified block before ratification")

    return emit(ID, "PASS", "settled scene-tag structure OK; per-tag rules left unratified (not invented)")


if __name__ == "__main__":
    sys.exit(main())
