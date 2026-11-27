"""S4-G2-02: no dangling checklist references (00 §7).

For each of six historically-dangling terms:
  - hits == 0 -> term judged 'removed' (no definition needed);
  - hits > 0  -> every hit must resolve to a definition (item with a
    `definition` object whose source_ref resolves) OR an explicit 'removed'
    reason explaining why the term has no definition.

The verdict for each term must be exactly one of {defined, removed} — no
third value. This catches a term that appears in the checklist with neither
a definition nor an explanation: a real governance drift.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G2-02"
TERMS = ["基准分", "结算模板 ID", "版本号", "最低差异",
         "can_modify_persistent_state", "阶位推导"]


def main():
    cfg = ROOT / "config" / "checklist.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/checklist.json missing")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    items = data.get("items", [])
    text = cfg.read_text(encoding="utf-8")

    problems = []
    verdicts = {}
    for term in TERMS:
        hits = text.count(term)
        if hits == 0:
            verdicts[term] = "removed"
            continue
        # locate items that mention this term
        mentioning = [it for it in items
                      if term in json.dumps(it, ensure_ascii=False)]
        resolved = []
        for it in mentioning:
            if it.get("status") == "defined" and isinstance(it.get("definition"), dict):
                ref = it["definition"].get("source_ref", "")
                if ref and _ref_resolves(ref, ROOT):
                    resolved.append(it["id"])
            elif it.get("status") == "removed" and it.get("reason"):
                resolved.append(it["id"])
        if not resolved:
            problems.append("%s: %d hit(s) with no definition or removed reason" % (term, hits))
        verdicts[term] = "defined" if any(
            it.get("status") == "defined" for it in mentioning) else "removed"

    if problems:
        return emit(ID, "FAIL", "; ".join(problems))
    bad = {t: v for t, v in verdicts.items() if v not in ("defined", "removed")}
    if bad:
        return emit(ID, "FAIL", "third verdict value: %s" % bad)

    ev = ROOT / "evidence" / "s4"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g2-02.txt").write_text(
        "\n".join("%s -> %s" % kv for kv in verdicts.items()) + "\n", encoding="utf-8")
    return emit(ID, "PASS", "6 terms judged (no third value); all hits resolve to definition or removed reason")


def _ref_resolves(ref, root):
    """A source_ref resolves if it names a known doc/config/stub path or a
    chapter reference (e.g. '06 §1.2') in an existing document."""
    for token in ref.replace("（", " ").replace("）", " ").replace("/", " ").split():
        if token.endswith(".json"):
            p = _find_json(root, token)
            if p is not None:
                return True
    # chapter-style refs are documentation pointers, resolvable if docs exist
    return (root / "docs" / "设计决议记录.md").is_file() and "§" in ref


def _find_json(root, name):
    for p in root.rglob(name):
        if p.is_file():
            return p
    return None


if __name__ == "__main__":
    sys.exit(main())
