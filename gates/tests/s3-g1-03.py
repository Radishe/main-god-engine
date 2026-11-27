"""S3-G1-03: the tier table has one identity across chapters (00 §6).

Chapters 04/05/07/09 must all reference config/tiers.json and none may
declare a second tier scale. This is a single-identity check on ratified
documentation, not a gameplay-number assertion.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S3-G1-03"
CHAPTERS = ["04", "05", "07", "09"]


def main():
    docs = list((ROOT / "docs").glob("*-*.md"))
    problems = []
    found = {}
    for ch in CHAPTERS:
        paths = [p for p in docs if p.name.startswith(ch + "-")]
        if not paths:
            problems.append("chapter %s missing" % ch)
            continue
        text = "\n".join(p.read_text(encoding="utf-8") for p in paths)
        has_ref = "config/tiers.json" in text or "tiers.json" in text
        found[ch] = has_ref
        if not has_ref:
            problems.append("chapter %s does not reference tiers.json" % ch)
        # a second identity would be another scale table declaration
        if re.search(r"阶位.{0,12}(区间表|刻度表).{0,20}(另|第二|独立)", text):
            problems.append("chapter %s declares a second tier identity" % ch)
    if problems:
        return emit(ID, "FAIL", "; ".join(problems))

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-03.txt").write_text(
        "chapters referencing config/tiers.json: " + ",".join(found) + "\n", encoding="utf-8")
    return emit(ID, "PASS", "4 chapters reference the single tier table, no second identity")


if __name__ == "__main__":
    sys.exit(main())
