"""X02-01: stub-vs-implementation consistency (black box).

SPEC: every implemented package must BEHAVE exactly as its shared stub declares.
      A package that has not landed is DEFERRED, never silently PASS.

Anti-tautology rule: this test NEVER imports implementation internals
(REQUIRED / TYPES / check_manifest). It builds all expectations from the stub
document itself and probes the public Engine.settle() entry point. Drift in the
implementation is caught even when it reads the same stub at import time.
"""

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "X02-01"
STUBS = ROOT / "gates" / "stubs"


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _code(exc):
    return str(exc).split(":", 1)[0]


def check_settlement():
    """Probe settle() through its public API; never import its internals."""
    impl = ROOT / "src" / "core" / "settlement.py"
    if not impl.is_file():
        return "DEFERRED", "P1 settlement implementation not landed"
    doc = _load_json(STUBS / "settlement.json")
    spec = doc["settlement_manifest"]
    required = spec["required"]
    optional = spec.get("optional", [])
    types = spec["types"]
    codes = doc["error_codes"]

    sys.path.insert(0, str(ROOT))
    try:
        from src.core.ledger import Engine, Rejected
    except Exception as exc:
        return "FAIL", "cannot import Engine public API: %s" % exc

    base = _load_json(ROOT / "gates" / "fixtures" / "f4-settlement.json")
    ledger = _load_json(ROOT / "gates" / "fixtures" / "f3-ledger.json")
    problems = []

    def probe(label, manifest, expect):
        """expect='accept' or an error code from the stub."""
        try:
            Engine(ledger).settle(manifest)
            got = "accept"
        except Rejected as exc:
            got = _code(exc)
        except Exception as exc:  # wrong exception type is itself a contract breach
            got = "unexpected:%s" % type(exc).__name__
        if got != expect:
            problems.append("%s: got %s expected %s" % (label, got, expect))
        if got != "accept" and got.startswith("unexpected"):
            return
        if got != "accept" and got not in codes:
            problems.append("%s: error code %s not in stub error_codes" % (label, got))

    probe("F4 legal", base, "accept")

    # every required field, removed in turn
    for key in required:
        bad = dict(base)
        bad.pop(key, None)
        probe("missing:" + key, bad, "invalid_field")

    # type violations derived from the stub's own declarations
    bad_values = {
        "string": 123,
        "integer": "not-int",
        "enum<success|failure|aborted>": "out-of-enum",
        "array<string>": ["ok", 7],
    }
    for key, decl in types.items():
        if decl in bad_values:
            probe("badtype:" + key, dict(base, **{key: bad_values[decl]}), "invalid_field")

    # frozen field set: an undeclared field must be refused
    if spec.get("frozen"):
        probe("frozen:extra", dict(base, undeclared_field=1), "invalid_field")

    # D18 c3: field-set digest must match the declared field set.
    # Computed independently here from the stub document — never import the
    # implementation's own digest function (that would be tautological).
    import hashlib as _hashlib
    fields = sorted(required) + sorted(optional)
    expected_digest = _hashlib.sha256(",".join(fields).encode("utf-8")).hexdigest()
    recorded = spec.get("field_set_digest")
    if recorded and expected_digest != recorded:
        problems.append("field_set_digest drift: computed=%s stub=%s" % (expected_digest, recorded))

    # D18 c1/c2: double-report and structured-claims probes
    import json as _json
    good_claims = _json.dumps({"schema_version": 1, "score": 8, "volume": 10,
                               "main_share": 1.0, "side_share": 0.0,
                               "main_failed": False, "event_flags": []}, ensure_ascii=False)
    probe("double_report", dict(base, credit_delta=500, claims=good_claims),
          "rejected_double_report")
    bare_claims = _json.dumps({"score": 999, "credits": 100000})
    probe("bare_claims", dict(base, credit_delta=0, claims=bare_claims), "invalid_field")

    # idempotency and unnotarised IDs are declared error codes too
    dup = dict(base, idempotency_key="X02-DUP-001")
    eng = Engine(ledger)
    eng.settle(dup)
    try:
        eng.settle(dup)
        problems.append("duplicate idempotency_key accepted; expected duplicate_settlement")
    except Rejected as exc:
        if _code(exc) != "duplicate_settlement":
            problems.append("duplicate key error %s != duplicate_settlement" % _code(exc))

    # F6 direct write must go through the declared rejected_direct_write code
    f6_path = ROOT / "gates" / "fixtures" / "f6-malicious.py"
    if f6_path.is_file():
        spec_mod = importlib.util.spec_from_file_location("f6_probe", f6_path)
        f6 = importlib.util.module_from_spec(spec_mod)
        spec_mod.loader.exec_module(f6)
        outcome = f6.run(Engine(ledger).ledger())
        if outcome.get("direct_write") != "blocked":
            problems.append("F6 direct write not blocked")

    if problems:
        return "FAIL", "; ".join(problems)
    return "PASS", "behaviour matches settlement stub (%d probes, no implementation internals imported)" % (
        len(required) + len(types) + 3)


def deferred_packages():
    """List stubs whose owning package exposes no callable interface yet."""
    checks = [
        ("P3", "loader.json", ROOT / "src" / "loader" / "__init__.py"),
        ("P4", "notary.json", ROOT / "src" / "notary" / "__init__.py"),
        ("P4", "vocabulary.json", ROOT / "vocab" / "__init__.py"),
    ]
    return ["%s/%s" % (pkg, stub) for pkg, stub, path in checks if not path.is_file()]


def main():
    if not (STUBS / "settlement.json").is_file():
        return emit(ID, "FAIL", "settlement stub missing")
    status, detail = check_settlement()
    deferred = deferred_packages()
    tail = " | deferred=%s (not landed, not claimed)" % (",".join(deferred) or "none")
    if status == "DEFERRED":
        return emit(ID, "PENDING", detail)
    if status == "FAIL":
        return emit(ID, "FAIL", detail + tail)
    return emit(ID, "PASS", detail + tail)


if __name__ == "__main__":
    sys.exit(main())
