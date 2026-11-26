"""C01-01: the main god is a rules engine; instances are data only.

D15: declarative JSON is the primary channel; DLL is an explicit opt-in. For the
primary channel, instance declarations must contain no settle/ledger-write/penalty
logic. Static scan hit count must be zero.

I3 companion: instances must not import engine internals.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "C01-01"
FORBIDDEN_TOKENS = ("settle(", "rejected_direct_write", "credit_delta =", "penalty(",
                    "from src.core", "import src.core", "from core.", "import ledger")


def main():
    cfg = ROOT / "config" / "contribution.json"
    if not cfg.is_file():
        return emit(ID, "PENDING", "D15 not fixed; contribution boundary whitelist unknown")
    rules = json.loads(cfg.read_text(encoding="utf-8"))
    if rules.get("primary_channel") != "declarative_json":
        return emit(ID, "FAIL", "primary channel is not declarative_json")

    scanned, hits = 0, []
    for base in (ROOT / "content" / "instances", ROOT / "gates" / "fixtures"):
        if not base.is_dir():
            continue
        for path in base.glob("*.json"):
            scanned += 1
            text = path.read_text(encoding="utf-8")
            for token in FORBIDDEN_TOKENS:
                if token in text:
                    hits.append("%s:%s" % (path.relative_to(ROOT), token))
    if hits:
        return emit(ID, "FAIL", "instance declarations contain engine logic: " + ", ".join(hits))
    if scanned == 0:
        return emit(ID, "FAIL", "no instance declarations scanned")
    return emit(ID, "PASS", "scanned %d declarations, 0 engine-logic hits" % scanned)


if __name__ == "__main__":
    sys.exit(main())
