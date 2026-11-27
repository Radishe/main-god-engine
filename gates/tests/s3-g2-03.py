"""S3-G2-03: scoring chain order is fixed (00 §6 / D20).

config/scoring.json declares chain = score -> achievement_rate -> grade ->
coefficient -> payout. grade must precede coefficient; the chain must be
single-valued and match the ratified D20 order. No runtime invention.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S3-G2-03"
WANT = ["score", "achievement_rate", "grade", "coefficient", "payout"]


def main():
    cfg = ROOT / "config" / "scoring.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "scoring.json missing")
    chain = json.loads(cfg.read_text(encoding="utf-8")).get("chain")
    if chain != WANT:
        return emit(ID, "FAIL", "chain drift: %r expected %r" % (chain, WANT))
    if chain.index("grade") > chain.index("coefficient"):
        return emit(ID, "FAIL", "grade after coefficient")

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g2-03.log").write_text(" -> ".join(chain) + "\n", encoding="utf-8")
    return emit(ID, "PASS", "scoring chain fixed: %s" % " -> ".join(chain))


if __name__ == "__main__":
    sys.exit(main())
