"""X03-01: config-change regression — S1 invariants still hold after D20/D21.

SPEC: run `check.py --stage s1 --run`; exit code must be 0, all 11 invariant
tests must PASS individually. If any turns red the config change is rejected.
Evidence is written to evidence/int/regression.log.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "X03-01"


def main():
    cfg = ROOT / "config"
    if not cfg.is_dir():
        return emit(ID, "PENDING", "no config directory yet")

    proc = subprocess.run(
        [sys.executable, str(ROOT / "gates" / "check.py"), "--stage", "s1", "--run"],
        capture_output=True, text=True, encoding="utf-8", timeout=120)
    out = proc.stdout or ""
    lines = [l for l in out.splitlines() if l.startswith("TEST ")]
    passes = [l for l in lines if " PASS " in l]
    non_pass = [l for l in lines if " PASS " not in l]

    ev = ROOT / "evidence" / "int"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "regression.log").write_text(
        "stage=s1 exit=%d\n" % proc.returncode + "\n".join(lines) + "\n", encoding="utf-8")

    if proc.returncode != 0:
        return emit(ID, "FAIL", "s1 exit=%d; non_pass=%s" % (
            proc.returncode, non_pass or "none"))
    if len(passes) != 11:
        return emit(ID, "FAIL", "expected 11 PASS lines, got %d" % len(passes))
    return emit(ID, "PASS", "s1 exit=0; %d/11 invariants PASS after config changes" % len(passes))


if __name__ == "__main__":
    sys.exit(main())
