"""S2-G3-02: death flow is defined and backfilled (00 §5 / D16 / D22).

The decision record plus config/states.json must settle three fields:
  - death attribution enum is single-valued;
  - counts toward erasure is a boolean;
  - lethal activation condition is decidable.
All three non-empty. Checks ratified structure; does not invent rules.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S2-G3-02"


def main():
    cfg = ROOT / "config" / "states.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/states.json missing")
    data = json.loads(cfg.read_text(encoding="utf-8"))

    # 1. death attribution enum single-valued: exit_and_settle (D16)
    death = data.get("death_flow")
    if death != "exit_and_settle":
        return emit(ID, "FAIL", "death_flow=%r expected exit_and_settle" % death)

    # 2. counts toward erasure is a boolean
    counts = data.get("counts_toward_erasure")
    if not isinstance(counts, bool):
        return emit(ID, "FAIL", "counts_toward_erasure not boolean: %r" % counts)

    # 3. lethal activation decidable: declared flag + D16 states it
    lethal = data.get("lethal_requires_declaration")
    if not isinstance(lethal, bool):
        return emit(ID, "FAIL", "lethal_requires_declaration not boolean: %r" % lethal)

    # decision record must backfill the enum + booleans (D16 body)
    dec = ROOT / "docs" / "设计决议记录.md"
    if not dec.is_file():
        return emit(ID, "FAIL", "decision record missing")
    import re
    m = re.search(r"^## D16\b.*?$(.*?)(?=^## |\Z)", dec.read_text(encoding="utf-8"), re.M | re.S)
    if not m or "退出并按未完成结算" not in m.group(1):
        return emit(ID, "FAIL", "D16 death attribution not backfilled")
    if "不复活" not in m.group(1) and data.get("revive") is not False:
        return emit(ID, "FAIL", "revive semantics not settled")

    ev = ROOT / "evidence" / "s2"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g3-02.md").write_text(
        "D16+D22 death flow: enum=exit_and_settle (single), "
        "counts_toward_erasure=%s (bool), lethal_requires_declaration=%s (bool)\n" %
        (counts, lethal), encoding="utf-8")
    return emit(ID, "PASS", "death flow defined: single enum, boolean count, decidable lethal")


if __name__ == "__main__":
    sys.exit(main())
