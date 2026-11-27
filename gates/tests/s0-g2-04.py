"""S0-G2-04: placeholders in paths.json are replaced (00 §3).

engine_core / test_runner / enum_source must exist and hold non-placeholder
values (no angle-bracket templates). The spec's original '<engine-core>'
etc. were §1.7 concept placeholders; actual keys are snake_case.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S0-G2-04"
KEYS = ["engine_core", "test_runner", "enum_source"]


def main():
    cfg = ROOT / "config" / "paths.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/paths.json missing")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    problems = []
    for k in KEYS:
        v = data.get(k)
        if not v or not isinstance(v, str):
            problems.append("%s missing/empty" % k)
        elif v.strip().startswith("<") or v.strip().endswith(">"):
            problems.append("%s still placeholder: %r" % (k, v))
    if problems:
        return emit(ID, "FAIL", "; ".join(problems))

    ev = ROOT / "evidence" / "s0"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g2-04.json").write_text(json.dumps(
        {k: data[k] for k in KEYS}, ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "paths placeholders resolved: %s" %
                ", ".join("%s=%s" % (k, data[k]) for k in KEYS))


if __name__ == "__main__":
    sys.exit(main())
