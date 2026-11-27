"""F5 six-variant + S3-G5 volume validation with location-aware errors.

No gameplay numbers are invented here. Every threshold/reference is read from
shared read-only sources:

  * field set / types / completion enum  -> gates/stubs/settlement.json (via
    src.core.settlement.check_manifest, the single structural source of truth)
  * notarized ability/item IDs           -> gates/stubs/vocabulary.json sources
  * "已加载副本 ID"                       -> content/instances/*/instance.json
  * total_volume contract                -> config/volume.json (ratified block);
    a numeric limit is only used when one is actually configured, never
    synthesized while max_total_volume is UNRATIFIED.
"""

import json
import re
from pathlib import Path

from ..core.ledger import Rejected
from ..core.settlement import check_manifest
from ..core import scoring  # D25: share rules — same function + same config truth-source

ROOT = Path(__file__).resolve().parents[2]
VOCAB_STUB = ROOT / "gates" / "stubs" / "vocabulary.json"
INSTANCES_DIR = ROOT / "content" / "instances"
VOLUME_CONFIG = ROOT / "config" / "volume.json"


class ContractViolation(Exception):
    """One clean, machine-readable rejection. Never carries a traceback."""

    def __init__(self, field, code, message, path=None, line=None):
        self.field = field
        self.code = code
        self.message = message
        self.path = path if path is not None else "$." + field
        self.line = line
        super().__init__(message)

    def render(self):
        return "REJECTED field=%s path=%s line=%s code=%s detail=%s" % (
            self.field,
            self.path,
            self.line if self.line is not None else "?",
            self.code,
            self.message,
        )


# --------------------------------------------------------------------------
# shared-source readers (read-only; no package may write these paths)
# --------------------------------------------------------------------------

def loaded_instance_ids():
    """IDs of instances that can be loaded, from content/instances/*/instance.json.

    Returns None when the instance tree is absent, so a caller without instance
    data is not rejected for a context it cannot know about.
    """
    if not INSTANCES_DIR.is_dir():
        return None
    ids = set()
    for path in sorted(INSTANCES_DIR.glob("*/instance.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and isinstance(data.get("instance_id"), str):
            ids.add(data["instance_id"])
    return ids or None


def notarized_ids():
    """{id: entry} from the vocabulary sources declared by the notary stub."""
    registry = {}
    if not VOCAB_STUB.is_file():
        return registry
    try:
        sources = json.loads(VOCAB_STUB.read_text(encoding="utf-8"))["sources"]
    except (OSError, ValueError, KeyError):
        return registry
    for rel in sources:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = data if isinstance(data, list) else data.get("entries", [])
        for entry in rows:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                registry[entry["id"]] = entry
    return registry


def volume_config(path=None):
    """Read config/volume.json (or an explicit path for test doubles)."""
    target = Path(path) if path else VOLUME_CONFIG
    if not target.is_absolute() and not target.is_file():
        target = ROOT / target
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def scene_config(path=None):
    """Read config/scenes.json ratified block (or an explicit dict/path for tests).

    D25: only an already-ratified, binary-judgable enum is enforced. When the
    config is missing / not ratified / unknown_tag_rejected is not True, this
    returns None and no scene-tag check runs — never invent a tag rule.
    """
    if isinstance(path, dict):
        data = path
    else:
        target = Path(path) if path else ROOT / "config" / "scenes.json"
        if not target.is_absolute() and not target.is_file():
            target = ROOT / target
        if not target.is_file():
            return None
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    if not isinstance(data, dict):
        return None
    ratified = data.get("ratified")
    if not isinstance(ratified, dict) or ratified.get("unknown_tag_rejected") is not True:
        return None
    enum = ratified.get("enum")
    if not isinstance(enum, list) or not enum:
        return None
    return ratified


def instance_document(instance_id, path=None):
    """Read content/instances/<id>/instance.json as (dict, raw_text).

    D25: scene_tag lives on the declaration side, never in the frozen
    settlement manifest. Missing/corrupt file -> (None, None), same tolerance
    as loaded_instance_ids().
    """
    if path is not None:
        target = Path(path)
        if not target.is_absolute() and not target.is_file():
            target = ROOT / target
    else:
        target = INSTANCES_DIR / str(instance_id) / "instance.json"
    if not target.is_file():
        return None, None
    try:
        text = target.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, ValueError):
        return None, None
    return (data, text) if isinstance(data, dict) else (None, None)


# --------------------------------------------------------------------------
# location helpers: field path + 1-based line number
# --------------------------------------------------------------------------

def _line_of(text, needle, occurrence=0):
    if not text:
        return None
    hits = list(re.finditer(re.escape(needle), text))
    if len(hits) <= occurrence:
        return None
    return text.count("\n", 0, hits[occurrence].start()) + 1


def _locate(text, field, index=None):
    """Return (field_path, line) for a top-level field, even when missing."""
    path = "$." + field if index is None else "$.%s[%d]" % (field, index)
    if not text:
        return path, None
    hits = list(re.finditer(r'"%s"\s*:' % re.escape(field), text))
    if hits:
        return path, text.count("\n", 0, hits[0].start()) + 1
    # missing field: point at the document root / closing brace
    return path, max(1, text.count("\n") + (0 if text.endswith("\n") else 1))


def _locate_value(text, field, value, occurrence=0):
    """Line of the nth JSON spelling of a value (for duplicate array items)."""
    return _line_of(text, json.dumps(value, ensure_ascii=False), occurrence)


def _first_duplicate(values):
    seen = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


def _violation_field(raw):
    """Extract the offending field name from a check_manifest Rejected message."""
    tail = str(raw).partition(":")[2]
    if not tail:
        return "manifest"
    # e.g. "invalid_field:claims:score" -> "claims" (the top-level field)
    return tail.split(",")[0].split(":")[0]


def _numeric_limit(cfg):
    """A configured numeric ceiling, or None while the decision is UNRATIFIED.

    Never guess a number: only an actual int/float in the config can drive a
    comparison (bool excluded because it is a subclass of int in Python).
    """
    if not cfg:
        return None
    for block in ("ratified", "unratified"):
        value = cfg.get(block, {}).get("max_total_volume")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate_manifest(manifest, *, text=None, source=None, instances=None,
                      notarized=None, volume=None, scene=None,
                      scene_instance=None, scene_instance_text=None):
    """Validate one settlement manifest; raise ContractViolation on the first breach.

    ``text`` is the original JSON text, used only to report a line number.
    ``instances`` / ``notarized`` / ``volume`` (and D25's ``scene`` /
    ``scene_instance`` / ``scene_instance_text``) are injectable context for
    tests; otherwise shared read-only sources are used.
    """
    region = source or "manifest"

    # Volume context first: config/volume.json ratifies total_volume as a
    # manifest field. The CLI contract layer honours that declaration; the
    # engine's frozen field set (I4) is left untouched.
    if isinstance(volume, (str, Path)) or volume is None:
        cfg = volume_config(volume)
    else:
        cfg = volume
    volume_field = cfg.get("ratified", {}).get("manifest_field") if cfg else None

    # 1. structural contract — stub-driven, identical to the engine's gate.
    structural = manifest
    if isinstance(manifest, dict) and volume_field and volume_field in manifest:
        structural = {k: v for k, v in manifest.items() if k != volume_field}
    try:
        check_manifest(structural)
        # D25: D20 share rules are already ratified and binary-judgable, so the
        # CLI enforces them too (previously only settle() did, too late for PR).
        # Same function + same config source as the engine — no duplicated rule.
        if isinstance(manifest, dict) and "claims" in manifest and scoring.is_enabled():
            scoring.validate_shares(scoring.decode_claims(manifest),
                                    scoring.load_config())
    except Rejected as exc:
        raw = str(exc)
        field = _violation_field(raw)
        code = raw.partition(":")[0]
        path, line = _locate(text, field)
        if field in ("item_ids", "ability_ids") and isinstance(manifest, dict):
            dup = _first_duplicate(manifest.get(field) or [])
            if dup is not None and text:
                values = list(manifest[field])
                index = values.index(dup, values.index(dup) + 1)
                line = _locate_value(text, field, dup, occurrence=1) or line
                path = "$.%s[%d]" % (field, index)
        raise ContractViolation(field, code, raw, path, line) from None

    if not isinstance(manifest, dict):
        raise ContractViolation("manifest", "invalid_field", "manifest is not an object",
                                "$", _line_of(text, "{") if text else None)

    # 2. F5-5 — instance_id must hit a loaded instance.
    loaded = instances if instances is not None else loaded_instance_ids()
    iid = manifest.get("instance_id")
    if loaded is not None and iid not in loaded:
        path, line = _locate(text, "instance_id")
        raise ContractViolation(
            "instance_id", "invalid_field",
            "instance_id %r is not a loaded instance (%s)" % (iid, region), path, line)

    # 2b. D25 — scene_tag is declared on the INSTANCE side (never in the frozen
    # settlement manifest). If C15's enum is ratified, reject unknown tags here.
    # The field name itself is read from config — no second source of truth.
    scene_cfg = scene_config() if scene is None else scene_config(scene)
    if scene_cfg is not None:
        field = scene_cfg.get("manifest_field")
        if isinstance(field, str) and field:
            if scene_instance is not None:
                doc = scene_instance
                scene_text = scene_instance_text
            else:
                doc, scene_text = instance_document(iid)
            if isinstance(doc, dict) and field in doc:
                tag = doc[field]
                if tag not in scene_cfg["enum"]:
                    path, line = _locate(scene_text, field)
                    raise ContractViolation(
                        field, "invalid_field",
                        "%s=%r not in ratified enum %s (source=instance.json)" % (
                            field, tag, scene_cfg["enum"]),
                        path, line)

    # 3. F5-3 — ability_ids must be notarized (hit vocabulary + apply to instance).
    registry = notarized if notarized is not None else notarized_ids()
    for index, aid in enumerate(manifest.get("ability_ids") or []):
        entry = registry.get(aid)
        if entry is None:
            path, _ = _locate(text, "ability_ids", index)
            line = _locate_value(text, "ability_ids", aid) if text else None
            raise ContractViolation(
                "ability_ids", "rejected_unnotarized",
                "ability_ids[%d] %r is not a notarized vocabulary id" % (index, aid),
                path, line)
        allowed = entry.get("enabled_in") if isinstance(entry, dict) else None
        if allowed and iid not in allowed:
            path, _ = _locate(text, "ability_ids", index)
            line = _locate_value(text, "ability_ids", aid) if text else None
            raise ContractViolation(
                "ability_ids", "rejected_unnotarized",
                "ability_ids[%d] %r is not notarized for instance %r" % (index, aid, iid),
                path, line)

    # item_ids carry the same notary rule; duplicates already rejected in step 1.
    for index, iid_value in enumerate(manifest.get("item_ids") or []):
        if iid_value not in registry:
            path, _ = _locate(text, "item_ids", index)
            line = _locate_value(text, "item_ids", iid_value) if text else None
            raise ContractViolation(
                "item_ids", "rejected_unnotarized",
                "item_ids[%d] %r is not a notarized vocabulary id" % (index, iid_value),
                path, line)

    # 4. S3-G5 — total_volume contract. Only a configured numeric ceiling is
    # enforced; a UNRATIFIED ceiling yields no invented number.
    if cfg and volume_field and volume_field in manifest:
        declared = cfg.get("ratified", {}).get("manifest_field", "total_volume")
        value = manifest["total_volume"]
        path, line = _locate(text, declared)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ContractViolation(
                declared, "invalid_field",
                "%s must be an integer, got %s" % (declared, type(value).__name__),
                path, line)
        limit = _numeric_limit(cfg)
        if limit is not None and value > limit:
            marker = cfg.get("ratified", {}).get("limit_placeholder") or cfg.get(
                "unratified", {}).get("max_total_volume", "UNRATIFIED")
            raise ContractViolation(
                declared, "volume_limit_exceeded",
                "%s=%s exceeds configured limit=%s (limit marker=%s)" % (
                    declared, value, limit, marker), path, line)

    return None


def validate_file(path, *, volume=None):
    """Validate a manifest file; raises ContractViolation with a real line number.

    ``volume`` may be an already-loaded config dict or a path to one.
    """
    target = Path(path)
    if not target.is_absolute() and not target.is_file():
        target = ROOT / target
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractViolation("manifest", "manifest_unreadable", str(exc), "$", None) from None
    try:
        manifest = json.loads(text)
    except ValueError as exc:
        raise ContractViolation(
            "manifest", "invalid_json", str(exc), "$", max(1, text.count("\n") + 1)) from None
    cfg = volume if isinstance(volume, dict) else volume_config(volume)
    return validate_manifest(manifest, text=text, source=str(target), volume=cfg)
