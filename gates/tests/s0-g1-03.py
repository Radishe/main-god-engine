"""S0-G1-03: meta-decisions must not smuggle gameplay numbers (00 §3).

SPEC: across the D14 and D15 decision bodies, numeric literals = 0
(ID labels D14/D15 themselves excluded). A decision that quietly writes a
concrete number (tax rate, threshold, attribute cap) is rejected — numbers
belong in config/*.json, ratified separately.

This is a real anti-smuggling check, not an existence check.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S0-G1-03"
DECISIONS = ROOT / "docs" / "设计决议记录.md"


def section_bodies(text):
    """Return the body text of ## D14 and ## D15 sections (up to next ##)."""
    out = {}
    for name in ("D14", "D15"):
        m = re.search(r"^## %s\b.*?$(.*?)(?=^## |\Z)" % re.escape(name),
                      text, re.M | re.S)
        if m:
            out[name] = m.group(1)
    return out


def main():
    if not DECISIONS.is_file():
        return emit(ID, "FAIL", "docs/设计决议记录.md missing")
    bodies = section_bodies(DECISIONS.read_text(encoding="utf-8"))
    if set(bodies) != {"D14", "D15"}:
        return emit(ID, "FAIL", "D14/D15 sections not found: %s" % sorted(bodies))

    hits = []
    for name, body in bodies.items():
        # strip decision-ID labels and document cross-references (08 章, §5,
        # C21 etc.) — those are pointers, not gameplay numbers
        clean = re.sub(r"\b[A-Z]{1,3}\d+\b", "", body)
        clean = re.sub(r"\d+(?:\.\d+)?\s*[章节条款]", "", clean)
        clean = re.sub(r"§\s*\d+", "", clean)
        for m in re.finditer(r"\d+(?:\.\d+)?", clean):
            hits.append("%s:%s" % (name, m.group(0)))
    if hits:
        return emit(ID, "FAIL", "numeric literal in meta-decision: " + ",".join(hits))

    ev = ROOT / "evidence" / "s0"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-03.txt").write_text(
        "scanned D14+D15 bodies; ID labels excluded; numeric literals=0\n",
        encoding="utf-8")
    return emit(ID, "PASS", "D14/D15 carry no gameplay numeric literals (IDs excluded)")


if __name__ == "__main__":
    sys.exit(main())
