"""C10-01: three admission checks (notary stub).

(1) axis declaration well-formed  (2) referenced asset IDs in library
(3) frozen admission snapshot. Each emits its own marker. Any failure rejects
the load and leaves the ledger unchanged.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
import src.notary as notary

ID = "C10-01"


def sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main():
    stub = ROOT / "gates" / "stubs" / "notary.json"
    if not stub.is_file():
        return emit(ID, "FAIL", "notary contract stub missing")
    markers_expected = json.loads(stub.read_text(encoding="utf-8"))["admission"]["log_markers"]
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    before = sha(ledger)
    good = {"axes": {"x": 1}, "asset_ids": ["item/known"]}
    library = {"item/known"}

    # all three pass: markers in declared order, snapshot equals ledger
    ok, marks, snap = notary.admit(good, ledger, asset_library=library)
    if not ok or marks != markers_expected:
        return emit(ID, "FAIL", "good admission markers %s != %s" % (marks, markers_expected))
    if snap != ledger or sha(ledger) != before:
        return emit(ID, "FAIL", "snapshot wrong or ledger mutated on admission")

    # fail case 1: no axes -> rejected, no markers
    ok1, m1, s1 = notary.admit({"asset_ids": []}, ledger, asset_library=library)
    if ok1 or m1 or s1 is not None:
        return emit(ID, "FAIL", "empty-axis instance was admitted")
    # fail case 2: unknown asset -> only first marker, rejected
    ok2, m2, s2 = notary.admit({"axes": {"x": 1}, "asset_ids": ["item/UNKNOWN"]},
                               ledger, asset_library=library)
    if ok2 or len(m2) != 1 or s2 is not None:
        return emit(ID, "FAIL", "unknown-asset instance was admitted: %s" % m2)
    if sha(ledger) != before:
        return emit(ID, "FAIL", "ledger changed on rejected admissions")

    ev = ROOT / "evidence" / "sc"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "c10-01.log").write_text(
        "markers=%s\nempty_axes=rejected\nunknown_asset=rejected\nledger_sha=%s\n" % (
            ",".join(marks), before), encoding="utf-8")
    return emit(ID, "PASS", "3 checks emit %s; failures reject with ledger unchanged" % markers_expected)


if __name__ == "__main__":
    sys.exit(main())
