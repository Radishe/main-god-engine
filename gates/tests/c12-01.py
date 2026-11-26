"""C12-01: instance code-channel import boundary (D15, notary/loader guard).

The loader loads declarative instances. Any instance declaring an import of an
engine-internal namespace (forbidden_imports.json) is rejected at load time
with rejected_import, and the violation is logged. D15 is ratified — the old
BLOCKER "D15 未定" is stale.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
import src.loader as loader

ID = "C12-01"


def main():
    cfg = ROOT / "config" / "contribution.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "contribution.json missing")
    d15 = json.loads(cfg.read_text(encoding="utf-8"))
    if d15.get("primary_channel") != "declarative_json":
        return emit(ID, "FAIL", "D15 primary channel not declarative JSON")
    fb = ROOT / "gates" / "stubs" / "forbidden_imports.json"
    if not fb.is_file():
        return emit(ID, "FAIL", "forbidden_imports.json missing")

    # legal declarative instance loads cleanly
    good = ROOT / "content" / "instances" / "F1" / "instance.json"
    loaded = loader.load(good)
    if loader.check_imports(loaded):
        return emit(ID, "FAIL", "legal instance flagged by import guard")

    # illegal instance: declares an engine-internal import -> rejected at load
    bad = {"instance_id": "EVIL", "axes": {"x": 1},
           "code": "from src.core.ledger import Engine"}
    violations = loader.check_imports(bad)
    if not violations:
        return emit(ID, "FAIL", "import guard missed forbidden token")

    err = ""
    with tempfile.TemporaryDirectory(prefix="c12-probe-") as tmp:
        p = Path(tmp) / "evil.json"
        p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        try:
            loader.load(p)
        except loader.LoadRejected as exc:
            err = str(exc)
        except Exception as exc:
            return emit(ID, "FAIL", "wrong exception type: %s" % type(exc).__name__)
    if "rejected_import" not in err:
        return emit(ID, "FAIL", "illegal instance not rejected with rejected_import: %r" % err)

    ev = ROOT / "evidence" / "sc"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "c12-01.log").write_text(
        "legal=F1 loaded\nillegal=%s\nviolations=%s\n" % (err, ",".join(violations)),
        encoding="utf-8")
    return emit(ID, "PASS", "declarative loads; import guard rejects engine imports (%s)" % violations)


if __name__ == "__main__":
    sys.exit(main())
