"""S0-G1-01: D14 is a decision entry with required fields.

Document-contract test: reads the decision log; no engine code involved.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S0-G1-01"


def main():
    doc = ROOT / "docs" / "设计决议记录.md"
    if not doc.is_file():
        return emit(ID, "FAIL", "decision log missing")
    text = doc.read_text(encoding="utf-8")
    if "## D14" not in text:
        return emit(ID, "FAIL", "D14 not written yet; expected red phase")
    section = text.split("## D14", 1)[1].split("\n## ", 1)[0]
    missing = [f for f in ("设计目的", "被否决选项及理由") if f not in section]
    if missing:
        return emit(ID, "FAIL", "D14 missing fields: " + ",".join(missing))
    return emit(ID, "PASS", "D14 complete")


if __name__ == "__main__":
    sys.exit(main())
