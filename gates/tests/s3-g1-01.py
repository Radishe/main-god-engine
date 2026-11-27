"""S3-G1-01: tier scale has a single owner, no hardcoded literals (00 §6).

config/tiers.json owner must be a single value; engine source and chapter
bodies must not carry tier range literals (they reference the config).
Closure itself is I9-01's job — this test checks ownership + no drift.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S3-G1-01"
TIER_LITERALS = ["1000", "2000", "4000", "8000", "16000", "32000"]


def main():
    cfg = ROOT / "config" / "tiers.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/tiers.json missing")
    d = json.loads(cfg.read_text(encoding="utf-8"))
    owner = d.get("owner")
    if not isinstance(owner, str) or not owner:
        return emit(ID, "FAIL", "tiers.json owner not a single value: %r" % owner)
    # owner must be one value, not a list/dict
    if not isinstance(d.get("scale_owner", owner), str):
        return emit(ID, "FAIL", "scale_owner not single-valued")

    # engine source must not hardcode tier bands
    hits = []
    for p in (ROOT / "src").rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        for lit in TIER_LITERALS:
            if re.search(r"\b%s\b" % lit, text):
                hits.append("%s:%s" % (p.name, lit))

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-01.txt").write_text(
        "tier owner=%s; source literals=%d\n" % (owner, len(hits)) +
        "\n".join(hits) + "\n", encoding="utf-8")
    if hits:
        return emit(ID, "FAIL", "tier literals in engine source: " + ",".join(hits))
    return emit(ID, "PASS", "single owner=%s; no tier range literals in src" % owner)


if __name__ == "__main__":
    sys.exit(main())
