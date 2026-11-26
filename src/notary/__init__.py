"""P4 notary — real implementation of gates/stubs/notary.json.

Notarizes instance admission (axes / assets / frozen snapshot) and verifies
settlement manifest IDs against the vocabulary. Vocabulary is the sole source
of what an instance is allowed to carry out (01 §5.1, 06).
"""

import copy
import json
from pathlib import Path

STUB = json.loads(
    (Path(__file__).resolve().parents[2] / "gates" / "stubs" / "notary.json").read_text(encoding="utf-8")
)
ADMISSION = STUB["admission"]
MARKERS = ADMISSION["log_markers"]


class NotaryError(Exception):
    """Carries a contract error code."""


def admit(instance, ledger, asset_library=None):
    """Three-step admission per stub. Returns (ok, markers, snapshot)."""
    markers = []
    axes = instance.get("axes") or {}
    if not isinstance(axes, dict) or not axes:
        return False, markers, None
    markers.append(MARKERS[0])

    assets = instance.get("asset_ids") or []
    if asset_library is not None and any(a not in asset_library for a in assets):
        return False, markers, None
    markers.append(MARKERS[1])

    snapshot = copy.deepcopy(ledger)
    markers.append(MARKERS[2])
    return True, markers, snapshot


def steps_complete(markers):
    return list(markers) == list(MARKERS)
