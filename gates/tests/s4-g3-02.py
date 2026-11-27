"""S4-G3-02: contribution protocol carries the three AI clauses (00 §7).

CONTRIBUTING.md must contain the AI-responsibility subsection, the training
data supply-chain statement and the maintainer removal-right statement.
Structural check on an existing ratified contract doc — deleting a clause
is caught.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G3-02"
TERMS = ["AI 辅助生成内容责任", "训练数据供应链", "项目方保留移除权"]


def main():
    doc = ROOT / "docs" / "CONTRIBUTING.md"
    if not doc.is_file():
        return emit(ID, "FAIL", "docs/CONTRIBUTING.md missing")
    text = doc.read_text(encoding="utf-8")
    missing = [t for t in TERMS if t not in text]
    if missing:
        return emit(ID, "FAIL", "AI clauses missing: " + ", ".join(missing))

    ev = ROOT / "evidence" / "s4"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-02.md").write_text(
        "CONTRIBUTING.md AI clauses present:\n" + "\n".join("- " + t for t in TERMS) + "\n",
        encoding="utf-8")
    return emit(ID, "PASS", "all 3 AI clauses present in contribution protocol")


if __name__ == "__main__":
    sys.exit(main())
