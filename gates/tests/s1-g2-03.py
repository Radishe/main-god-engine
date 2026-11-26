"""S1-G2-03: illegal manifest is rejected and ledger unchanged (00 §4).

F5-1 = a settlement manifest whose credit_delta is a string. The real engine
must reject it with invalid_field:credit_delta, leave the ledger byte-identical,
and the error output must name the offending field.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
from src.core.ledger import Engine, Rejected

ID = "S1-G2-03"


def sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main():
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    before = sha(ledger)

    # F5-1: credit_delta is a string (illegal per stub type)
    bad = dict(f4, credit_delta="not-an-integer", idempotency_key="S1-G2-03-F5")
    err = ""
    try:
        Engine(ledger).settle(bad)
    except Rejected as exc:
        err = str(exc)
    except Exception as exc:
        return emit(ID, "FAIL", "wrong exception type: %s" % type(exc).__name__)

    if not err:
        return emit(ID, "FAIL", "illegal manifest F5-1 was accepted")
    if "credit_delta" not in err:
        return emit(ID, "FAIL", "error does not name credit_delta: %s" % err)
    if sha(ledger) != before:
        return emit(ID, "FAIL", "ledger changed on rejected manifest")

    ev = ROOT / "evidence" / "s1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g2-03.log").write_text(
        "F5-1 rejected: %s\nledger_sha_before=%s\nledger_sha_after=%s\n" % (
            err, before, sha(ledger)), encoding="utf-8")
    return emit(ID, "PASS", "F5-1 rejected (%s); ledger unchanged" % err)


if __name__ == "__main__":
    sys.exit(main())
