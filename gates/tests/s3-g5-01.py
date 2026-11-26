"""S3-G5-01: inflated total-volume rejection — SETTLED part (C25-style).

SPEC (00 §6): a manifest declaring total_volume above the configured ceiling
is rejected; error names total_volume and includes the limit.

T4's concrete ceiling is NOT RATIFIED (the maintainer explicitly has no value).
This test asserts the settled structural contract and rejects any attempt to
smuggle a numeric ceiling into config/volume.json before ratification — exactly
the C15/C16/C25 pattern. No limit value is invented here.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S3-G5-01"


def main():
    cfg = ROOT / "config" / "volume.json"
    if not cfg.is_file():
        return emit(ID, "PENDING", "config/volume.json not produced")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    ratified = data.get("ratified", {})
    checks = {
        "manifest_field": "total_volume",
        "must_declare": True,
        "declared_by": "instance_author",
        "over_limit_rejected": True,
        "error_names_field": "total_volume",
        "error_field": "total_volume",
        "error_includes_limit_placeholder": True,
        "limit_placeholder": "UNRATIFIED",
        "rejection_exit_nonzero": True,
    }
    drift = ["%s=%r expected %r" % (k, ratified.get(k), v)
             for k, v in checks.items() if ratified.get(k) != v]
    if drift:
        return emit(ID, "FAIL", "volume.json ratified drift: " + "; ".join(drift))

    # the ceiling must stay explicitly unratified — no smuggled number anywhere
    unrat = data.get("unratified", {})
    if unrat.get("max_total_volume") != "UNRATIFIED":
        return emit(ID, "FAIL", "max_total_volume must stay UNRATIFIED")
    numeric = [k for k, v in ratified.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if numeric:
        return emit(ID, "FAIL", "numeric ceiling in ratified block: " + ",".join(numeric))

    # CLI must not invent a ceiling while T4 is unratified: a manifest that
    # declares a (structurally large) total_volume must still pass if no
    # numeric limit is configured.
    cli = ROOT / "tools" / "validate.py"
    if cli.is_file():
        fx = ROOT / "tests" / "p2" / "fixtures" / "F4-legal.json"
        if fx.is_file():
            proc = subprocess.run([sys.executable, str(cli), str(fx),
                                   "--volume-config", str(cfg)], cwd=str(ROOT),
                                  capture_output=True, text=True, encoding="utf-8")
            if proc.returncode != 0:
                return emit(ID, "FAIL", "CLI invented a ceiling under UNRATIFIED: %s" %
                            ((proc.stdout or "")[:200]))

    return emit(ID, "PASS", "settled volume contract OK; ceiling left UNRATIFIED (not invented)")


if __name__ == "__main__":
    sys.exit(main())
