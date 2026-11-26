"""P3 instance loader — real implementation of gates/stubs/loader.json.

Declarative JSON is the primary channel (D15). The engine is axis-agnostic:
axis names belong to the instance; the loader walks whatever keys the instance
declares without hard-coding any of them in the engine core (I2/D1).
"""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUB_PATH = ROOT / "gates" / "stubs" / "loader.json"
STUB = json.loads(STUB_PATH.read_text(encoding="utf-8"))
FORBIDDEN_PATH = ROOT / "gates" / "stubs" / "forbidden_imports.json"
FORBIDDEN = json.loads(FORBIDDEN_PATH.read_text(encoding="utf-8"))["forbidden_tokens"] if FORBIDDEN_PATH.is_file() else []


def check_imports(instance):
    """D15/C12: reject instances that import engine internals.

    Scans every string value in the declaration for forbidden import tokens.
    Returns a list of 'path:token' violations (empty = clean). No engine module
    is imported by the instance; the boundary is enforced here at load time.
    """
    violations = []

    def walk(value, path):
        if isinstance(value, str):
            for token in FORBIDDEN:
                if token in value:
                    violations.append("%s:%s" % (path, token))
        elif isinstance(value, dict):
            for k, v in value.items():
                walk(v, "%s.%s" % (path, k) if path else k)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, "%s[%d]" % (path, i))

    walk(instance, "")
    return violations


class LoadRejected(Exception):
    """An instance was refused at load time. Message carries the error code."""


def load(instance_path):
    """Load a declarative instance JSON. Returns a parsed instance dict.

    D15/C12: an instance that declares engine-internal imports is rejected with
    rejected_import before it can run. Declarative instances have no such tokens.
    """
    path = Path(instance_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("instance must be a JSON object")
    violations = check_imports(data)
    if violations:
        raise LoadRejected("rejected_import:" + ",".join(violations))
    return data


def axes_of(instance):
    """Return the instance's declared axes as {axis_name: value}.

    Generic walk over the 'axes' object — no axis name literals here.
    """
    axes = instance.get("axes") or {}
    if not isinstance(axes, dict):
        raise ValueError("axes must be an object")
    return {k: v for k, v in axes.items()}


def apply_event(instance, tick):
    """Apply one declared event generically: event names an axis + delta.

    The event targets whatever axis the instance declared; the loader never
    knows which axis that is. Returns an updated axes dict (does not mutate the
    instance) plus the event marker.
    """
    events = instance.get("events") or []
    target = None
    for ev in events:
        if ev.get("tick") == tick:
            target = ev
            break
    if target is None:
        raise ValueError("no event at tick %s" % tick)
    axis = target["axis"]
    axes = axes_of(instance)
    if axis not in axes:
        raise ValueError("event references undeclared axis")
    if not isinstance(axes[axis], int) or isinstance(axes[axis], bool):
        raise ValueError("axis value must be integer")
    result = dict(axes)
    result[axis] = result[axis] + target["delta"]
    return result, axis


def render_profile(instance):
    """Return the render profile metadata (D17: metadata placeholder only)."""
    rp = instance.get("render_profile")
    values = STUB["render_profile"]["values"]
    return rp if rp in values else None


def frozen_snapshot(ledger):
    """Admission snapshot: a deep copy, immutable during the instance (stub)."""
    return copy.deepcopy(ledger)
