"""Contract-level test double for settle().

Implements gates/stubs/settlement.json. This is NOT the product implementation:
package self-checks use it so P4 does not wait for P1; integrated correctness
is verified separately by X04-01 / C30-01.
"""

import copy
import json
from pathlib import Path

STUB = json.loads((Path(__file__).parent / "settlement.json").read_text(encoding="utf-8"))
REQUIRED = STUB["settlement_manifest"]["required"]
TYPES = STUB["settlement_manifest"]["types"]


class Rejected(Exception):
    pass


def _matches(decl, value):
    if decl == "string":
        return isinstance(value, str)
    if decl == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if decl.startswith("array<"):
        return isinstance(value, list)
    if decl.startswith("enum<"):
        return value in decl[5:-1].split("|")
    return True


def settle(ledger, manifest, registry=None):
    """Return a NEW ledger dict; never mutate the input."""
    missing = [k for k in REQUIRED if k not in manifest]
    if missing:
        raise Rejected("invalid_field:" + ",".join(missing))
    for key, decl in TYPES.items():
        if key in manifest and not _matches(decl, manifest[key]):
            raise Rejected("invalid_field:" + key)
    ids = list(manifest.get("ability_ids", [])) + list(manifest.get("item_ids", []))
    if registry is not None:
        unknown = [i for i in ids if i not in registry]
        if unknown:
            raise Rejected("rejected_unnotarized:" + ",".join(unknown))
    out = copy.deepcopy(ledger)
    out["credits"] = out.get("credits", 0) + manifest["credit_delta"]
    return out
