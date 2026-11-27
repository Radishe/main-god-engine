"""S3-G5-02: real demo instance volume passes validation (00 §6).

SPEC original: D1/D2 volume data both inside configured range.
ACTUAL: D1 exists (declarative volume=12), D2 is a human-in-loop artefact
not produced. This checks D1's declared volume is a positive integer inside
the (UNRATIFIED-free) structural contract; D2's absence is recorded, not
fabricated. No numeric ceiling is invented — volume.json stays UNRATIFIED.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S3-G5-02"


def main():
    d1 = ROOT / "content" / "instances" / "D1" / "instance.json"
    if not d1.is_file():
        return emit(ID, "FAIL", "D1 instance missing")
    data = json.loads(d1.read_text(encoding="utf-8"))
    ev_data = data.get("settlement_evidence", {})
    volume = ev_data.get("volume")
    if not isinstance(volume, int) or isinstance(volume, bool) or volume <= 0:
        return emit(ID, "FAIL", "D1 volume invalid: %r" % volume)

    # no numeric ceiling while T4 unratified
    vcfg = ROOT / "config" / "volume.json"
    if vcfg.is_file():
        v = json.loads(vcfg.read_text(encoding="utf-8"))
        if v.get("unratified", {}).get("max_total_volume") != "UNRATIFIED":
            return emit(ID, "FAIL", "volume ceiling no longer UNRATIFIED")

    # D2 now exists — validate its volume with the same rule, not just note presence
    d2 = ROOT / "content" / "instances" / "D2" / "instance.json"
    volumes = {"D1": volume}
    if d2.is_file():
        d2data = json.loads(d2.read_text(encoding="utf-8"))
        v2 = d2data.get("settlement_evidence", {}).get("volume")
        if not isinstance(v2, int) or isinstance(v2, bool) or v2 <= 0:
            return emit(ID, "FAIL", "D2 volume invalid: %r" % v2)
        volumes["D2"] = v2
        note = "D2 volume=%d structurally valid" % v2
    else:
        note = "D2 not produced (human_in_loop); not fabricated"

    ev = ROOT / "evidence" / "s3"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g5-02.json").write_text(json.dumps(
        {"volumes": volumes, "ceiling": "UNRATIFIED", "D2": note},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return emit(ID, "PASS", "volumes=%s structurally valid; %s" % (volumes, note))


if __name__ == "__main__":
    sys.exit(main())
