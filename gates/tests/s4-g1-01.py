"""S4-G1-01: validation CLI rejects all six illegal variants (00 §7 §1.2).

Each F5 variant must be rejected (non-zero), its error output must name the
expected field and a location (path/line), and stdout must contain no raw
traceback. This is structural — no gameplay numbers are asserted.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G1-01"
EXPECTED = {
    "F5-1": "credit_delta",
    "F5-2": "reincarnator_id",
    "F5-3": "ability_ids",
    "F5-4": "completion",
    "F5-5": "instance_id",
    "F5-6": "item_ids",
}


def main():
    cfg = ROOT / "config" / "paths.json"
    if not cfg.is_file():
        return emit(ID, "FAIL", "config/paths.json not registered by S0")
    cli = json.loads(cfg.read_text(encoding="utf-8")).get("validation_cli")
    if not cli or not (ROOT / cli).is_file():
        return emit(ID, "FAIL", "validation CLI not implemented")

    # legal F4 must still pass
    ok = subprocess.run([sys.executable, str(ROOT / cli)], cwd=str(ROOT),
                        capture_output=True, text=True, encoding="utf-8")
    if ok.returncode != 0:
        return emit(ID, "FAIL", "legal F4 rejected by CLI: %s" % (ok.stdout or "")[:200])

    problems = []
    for vid, field in EXPECTED.items():
        fx = ROOT / "tests" / "p2" / "fixtures" / (vid + ".json")
        if not fx.is_file():
            problems.append("%s fixture missing" % vid)
            continue
        proc = subprocess.run([sys.executable, str(ROOT / cli), str(fx)], cwd=str(ROOT),
                              capture_output=True, text=True, encoding="utf-8")
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            problems.append("%s accepted (exit=0)" % vid)
        elif field not in out:
            problems.append("%s error missing field %s" % (vid, field))
        elif "Traceback" in out:
            problems.append("%s leaked raw traceback" % vid)
        elif "path=" not in out and "line=" not in out:
            problems.append("%s error has no location" % vid)
    if problems:
        return emit(ID, "FAIL", "; ".join(problems))

    ev = ROOT / "evidence" / "s4"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-01.log").write_text(
        "legal F4: exit=0\n" + "\n".join("%s: rejected field=%s" % kv for kv in EXPECTED.items()) + "\n",
        encoding="utf-8")
    return emit(ID, "PASS", "F4 accepted; all 6 variants rejected with field+location, no traceback")


if __name__ == "__main__":
    sys.exit(main())
