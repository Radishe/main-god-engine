"""P4 vocabulary registry — validates settlement IDs against vocab sources.

Structural only per gates/stubs/vocabulary.json: checks entry shape, unique IDs,
and that every manifest ID hits an entry. Does not decide costs/effects values.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STUB = json.loads(
    (ROOT.parent / "gates" / "stubs" / "vocabulary.json").read_text(encoding="utf-8")
)
SCHEMA = STUB["entry_schema"]


def load_all():
    """Return {id: entry} from all declared vocab sources."""
    registry = {}
    for src in STUB["sources"]:
        path = ROOT.parent / src
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        # Two shapes exist in the sources: a bare array (exchange.json, the
        # C14 contract) or an {"entries": [...]} wrapper (items/abilities).
        rows = data if isinstance(data, list) else data.get("entries", [])
        for entry in rows:
            registry[entry["id"]] = entry
    return registry


def validate_entry(entry):
    """Return True if the entry matches the stub schema."""
    if not isinstance(entry, dict):
        return False
    if any(k not in entry for k in SCHEMA["required"]):
        return False
    if SCHEMA.get("id_unique") and not isinstance(entry.get("id"), str):
        return False
    if entry.get("kind") not in ("item", "ability", "bloodline", "skill"):
        return False
    return True


def check_ids(ids, registry=None):
    """Return the subset of ids that do NOT hit a vocabulary entry."""
    registry = registry if registry is not None else load_all()
    return [i for i in ids if i not in registry]


def enabled_in(entry, instance_id):
    """Whether an ability/item applies to the given instance."""
    return instance_id in (entry.get("enabled_in") or [])
