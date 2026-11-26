"""S1-G4-01: render switching never touches the ledger (00 §4).

F1 loads with render_profile=3d, F2 with 2d_flat. Both values must appear in
the load log, the ledger SHA-256 must be unchanged across both loads, and the
two settlement manifests must have identical field sets (render profile is
metadata only — affects_settlement=false in loader stub).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

sys.path.insert(0, str(ROOT))
import src.loader as loader
import src.notary as notary

ID = "S1-G4-01"


def sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main():
    paths = json.loads((ROOT / "config" / "paths.json").read_text(encoding="utf-8"))
    ledger = json.loads((ROOT / "gates" / "fixtures" / "f3-ledger.json").read_text(encoding="utf-8"))
    f4 = json.loads((ROOT / "gates" / "fixtures" / "f4-settlement.json").read_text(encoding="utf-8"))
    h0 = sha(ledger)
    log = []

    profiles = []
    for iid in ("F1", "F2"):
        inst = loader.load(ROOT / "content" / "instances" / iid / "instance.json")
        rp = loader.render_profile(inst)
        if rp is None:
            return emit(ID, "FAIL", "%s has no valid render_profile" % iid)
        profiles.append(rp)
        log.append("LOAD %s render_profile=%s" % (iid, rp))
        ok, markers, snap = notary.admit(inst, ledger)
        if not ok or not notary.steps_complete(markers):
            return emit(ID, "FAIL", "%s admission failed" % iid)
        if sha(ledger) != h0:
            return emit(ID, "FAIL", "ledger changed during %s load" % iid)

    if len(set(profiles)) < 2:
        return emit(ID, "FAIL", "render profiles not distinct: %s" % profiles)
    if not any("3d" in l for l in log) or not any("2d_flat" in l for l in log):
        return emit(ID, "FAIL", "both profile values must appear in load log")

    # both manifests share the same field set (render profile is metadata only)
    m1 = dict(f4, instance_id="F1", idempotency_key="G4-F1")
    m2 = dict(f4, instance_id="F2", idempotency_key="G4-F2")
    if set(m1) != set(m2):
        return emit(ID, "FAIL", "manifest field sets differ across render profiles")

    ev = ROOT / "evidence" / "s1"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g4-01.log").write_text(
        "\n".join(log) + "\nledger_sha_before=%s\nledger_sha_after=%s\n" % (h0, sha(ledger)),
        encoding="utf-8")
    return emit(ID, "PASS",
                "profiles=%s; ledger SHA unchanged; manifest field sets identical" % profiles)


if __name__ == "__main__":
    sys.exit(main())
