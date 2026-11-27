"""S0-G3-01: freeze list is effective (00 §11).

config/freeze.json must list every path that 00 §11 marks as frozen, with
the same count. This is a transcription check of a settled list — no new
paths are invented here.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S0-G3-01"


def main():
    spec = ROOT / "docs" / "00-阶段与验收标准.md"
    cfg = ROOT / "config" / "freeze.json"
    if not spec.is_file() or not cfg.is_file():
        return emit(ID, "FAIL", "spec or config/freeze.json missing")
    text = spec.read_text(encoding="utf-8")

    # extract the §11 '冻结' paragraph (first line after the heading)
    m = re.search(r"^## 11\.(.*?)(?=\n## |\Z)", text, re.M | re.S)
    if not m:
        return emit(ID, "FAIL", "§11 section not found")
    section = m.group(1)
    fm = re.search(r"\*\*冻结\*\*[：:]\s*(.*?)(?:\n|$)", section)
    if not fm:
        return emit(ID, "FAIL", "§11 freeze line not found")
    frozen_line = fm.group(1)
    # count distinct frozen entries separated by '、' (excluding trailing 。)
    expected = [p.strip() for p in frozen_line.rstrip("。 ").split("、") if p.strip()]

    data = json.loads(cfg.read_text(encoding="utf-8"))
    listed = [e.get("path", "") for e in data.get("frozen", [])]
    if len(listed) != len(expected):
        return emit(ID, "FAIL", "freeze count %d != §11 count %d" % (len(listed), len(expected)))
    # every config entry must correspond to a token in the §11 line
    missing = [p for p in listed if p not in frozen_line]
    if missing:
        return emit(ID, "FAIL", "freeze.json entries not in §11: " + ",".join(missing))

    ev = ROOT / "evidence" / "s0"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-01.json").write_text(json.dumps(
        {"frozen": listed, "count": len(listed), "matches_spec_11": True},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "freeze list effective: %d paths match §11" % len(listed))


if __name__ == "__main__":
    sys.exit(main())
