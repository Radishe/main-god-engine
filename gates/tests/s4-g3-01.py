"""S4-G3-01: contribution contract documents exist (00 §7).

Four docs exist, are non-empty, and contain every section title registered in
config/docs.json. Structural check only — no unratified rules are asserted.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G3-01"


def main():
    cfg = ROOT / "config" / "docs.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/docs.json missing (P6 deliverable)")
    docs = json.loads(cfg.read_text(encoding="utf-8")).get("documents", {})
    if len(docs) != 4:
        return emit(ID, "FAIL", "expected 4 registered documents, got %d" % len(docs))

    problems = []
    for rel, spec in docs.items():
        path = ROOT / rel
        if not path.is_file():
            problems.append("%s missing" % rel)
            continue
        text = path.read_text(encoding="utf-8")
        if len(text.strip()) == 0:
            problems.append("%s empty" % rel)
            continue
        for title in spec.get("required_sections", []):
            if title not in text:
                problems.append("%s missing section %r" % (rel, title))
    if problems:
        return emit(ID, "FAIL", "; ".join(problems))
    return emit(ID, "PASS", "4 docs non-empty with all registered sections")


if __name__ == "__main__":
    sys.exit(main())
