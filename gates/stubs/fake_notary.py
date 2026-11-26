"""Contract-level test double for admission notarization.

Implements gates/stubs/notary.json. Package self-checks use it so P3/P4 do not
wait for each other; integrated correctness is verified by X04-01 / C30-01.
"""

import copy
import json
from pathlib import Path

STUB = json.loads((Path(__file__).parent / "notary.json").read_text(encoding="utf-8"))
STEPS = STUB["admission"]["steps"]
MARKERS = STUB["admission"]["log_markers"]


def admit(instance, ledger, asset_library=None, axis_validator=None):
    """Return (ok, markers, snapshot). Never mutates ledger."""
    markers = []
    axes = instance.get("axes") or []
    if not axes or (axis_validator is not None and not axis_validator(axes)):
        return False, markers, None
    markers.append(MARKERS[0])
    assets = instance.get("asset_ids") or []
    if asset_library is not None and any(a not in asset_library for a in assets):
        return False, markers, None
    markers.append(MARKERS[1])
    snapshot = copy.deepcopy(ledger)
    markers.append(MARKERS[2])
    return True, markers, snapshot


def assert_steps_complete(markers):
    return markers == list(MARKERS)
