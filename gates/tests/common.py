"""Shared reporting protocol for gate tests.

Every test prints exactly one line: TEST <ID> <PASS|FAIL|PENDING> <reason>
Exit codes: PASS=0, FAIL=1, PENDING=2.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXIT = {"PASS": 0, "FAIL": 1, "PENDING": 2}


def gate_status(test_id):
    """Read the manifest so a skeleton never contradicts its gate status."""
    try:
        with (ROOT / "gates" / "manifest.json").open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        for gates in data["stages"].values():
            for gate in gates:
                if test_id in gate["tests"]:
                    return gate.get("status", "active")
    except (OSError, ValueError):
        pass
    return "active"


def emit(test_id, status, reason):
    print("TEST %s %s %s" % (test_id, status, reason))
    return EXIT[status]


def stage_skeleton(test_id, spec_ref, requires=()):
    """Executable entry point for a contract whose assertion lives in 00.

    PENDING when an upstream config is not fixed; FAIL when the spec is known
    but the implementation is missing. Never silently passes.
    """
    missing = [r for r in requires if not (ROOT / r).is_file()]
    if missing:
        if gate_status(test_id) == "pending":
            return emit(test_id, "PENDING", "spec %s needs %s" % (spec_ref, ",".join(missing)))
        return emit(test_id, "FAIL", "spec %s needs %s" % (spec_ref, ",".join(missing)))
    return emit(test_id, "FAIL", "spec %s needs implementation; expected red phase" % spec_ref)
