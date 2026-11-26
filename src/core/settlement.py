"""Manifest validation driven by the shared contract stub, not by a local copy.

D18: adds field-set digest verification (constraint 3), structured claims
validation (constraint 2), and double-report rejection (constraint 1).
"""

import hashlib
import json
from pathlib import Path

from .ledger import Rejected

STUB = json.loads(
    (Path(__file__).resolve().parents[2] / "gates" / "stubs" / "settlement.json").read_text(
        encoding="utf-8"
    )
)
SPEC = STUB["settlement_manifest"]
REQUIRED = SPEC["required"]
TYPES = SPEC["types"]
CLAIMS = STUB.get("claims_schema", {})


def field_set_digest():
    """sha256 of sorted(required)+sorted(optional) joined by comma."""
    fields = sorted(REQUIRED) + sorted(SPEC.get("optional", []))
    return hashlib.sha256(",".join(fields).encode("utf-8")).hexdigest()


def verify_field_set():
    """D18 c3: refuse to operate if the implementation's field set drifted
    from the digest recorded in the stub. Any extension needs a maintainer
    stub change + digest update + independent review."""
    recorded = SPEC.get("field_set_digest")
    if recorded and recorded != field_set_digest():
        raise Rejected("invalid_field:field_set_digest")


def _matches(decl, value):
    if decl == "string":
        return isinstance(value, str)
    if decl == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if decl == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if decl == "boolean":
        return isinstance(value, bool)
    if decl.startswith("array<"):
        item_decl = decl[6:-1]
        return isinstance(value, list) and all(_matches(item_decl, v) for v in value)
    if decl.startswith("enum<"):
        return isinstance(value, str) and value in decl[5:-1].split("|")
    raise Rejected("invalid_field:unknown_type_declaration")  # no silent pass-through


def _check_claims(raw):
    """D18 c2: claims must be structured evidence, never a bare payout."""
    if not isinstance(raw, str):
        raise Rejected("invalid_field:claims")
    try:
        claims = json.loads(raw)
    except (ValueError, TypeError):
        raise Rejected("invalid_field:claims")
    if not isinstance(claims, dict):
        raise Rejected("invalid_field:claims")
    if not CLAIMS:
        raise Rejected("invalid_field:claims_schema_missing")
    forbidden = set(CLAIMS.get("forbidden_bare_keys", []))
    if forbidden & set(claims):
        raise Rejected("invalid_field:claims:" + ",".join(sorted(forbidden & set(claims))))
    missing = [k for k in CLAIMS.get("required", []) if k not in claims]
    if missing:
        raise Rejected("invalid_field:claims:" + ",".join(missing))
    for key, decl in CLAIMS.get("types", {}).items():
        if key in claims and not _matches(decl, claims[key]):
            raise Rejected("invalid_field:claims:" + key)
    return claims


def check_manifest(manifest, scoring_enabled=False):
    """Raise Rejected('invalid_field:<name>') on the first contract violation."""
    verify_field_set()
    if not isinstance(manifest, dict):
        raise Rejected("invalid_field:manifest")
    missing = [k for k in REQUIRED if k not in manifest]
    if missing:
        raise Rejected("invalid_field:" + ",".join(missing))
    if SPEC.get("frozen"):
        allowed = set(REQUIRED) | set(SPEC.get("optional", []))
        extra = [k for k in manifest if k not in allowed]
        if extra:
            raise Rejected("invalid_field:" + ",".join(extra))
    for key, decl in TYPES.items():
        if key in manifest and not _matches(decl, manifest[key]):
            raise Rejected("invalid_field:" + key)
    if len(set(manifest.get("item_ids", []))) != len(manifest.get("item_ids", [])):
        raise Rejected("invalid_field:item_ids")
    if len(set(manifest.get("ability_ids", []))) != len(manifest.get("ability_ids", [])):
        raise Rejected("invalid_field:ability_ids")

    # D18 c1: claims and a NON-ZERO credit_delta are always mutually exclusive.
    # credit_delta stays required by the frozen field set, so a claims-based
    # manifest carries credit_delta=0 (not an authority) — any non-zero value
    # alongside claims is an attempt to report two payout sources and is refused
    # even before the chain is enabled. This closes the double-report loophole
    # at the structural layer so X02 can probe it today.
    if "claims" in manifest and manifest.get("credit_delta", 0) != 0:
        raise Rejected("rejected_double_report:claims+credit_delta")
    if "claims" in manifest:
        # validate structure even before the chain is enabled, so malformed
        # claims never sit in the pipeline waiting to become a payout.
        _check_claims(manifest["claims"])
