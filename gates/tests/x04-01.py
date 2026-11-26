"""X04-01: package-merge integration runner.

SPEC: assemble P1~P7 outputs and execute gates/integration_job.json's run_order
      in one run. Every step must exit 0 with zero FAIL and zero PENDING.
      Per-package green is never sufficient evidence for this gate.

This is an orchestrator, not a re-implementation: stub consistency is checked by
X02-01 (one of the ordered steps), the golden path by C30-01, invariants by I1~I8.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "X04-01"
# common.ROOT is already the project root (tests/ -> gates/ -> games/).
PROJECT_ROOT = ROOT
GATES = ROOT / "gates"
JOB = GATES / "integration_job.json"
CHECK = GATES / "check.py"
TESTS = GATES / "tests"
LOG = ROOT / "evidence" / "int" / "integration.log"


def run_step(cmd, cwd):
    """Run one argv list; return (exit_code, combined output)."""
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8")
    text = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, text.strip()


def statuses(text):
    """Collect TEST <id> <STATUS> lines from a step's output."""
    out = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "TEST" and parts[2] in ("PASS", "FAIL", "PENDING"):
            out.append((parts[1], parts[2]))
    return out


def expand_run_order(job):
    """Turn integration_job.json run_order strings into executable steps."""
    steps = []
    for item in job.get("run_order", []):
        if item.startswith("check.py "):
            args = item.split()[1:]
            steps.append(("cmd", item, [sys.executable, str(CHECK)] + args))
        elif item.startswith("I1..I8"):
            steps.append(("cmd", item, [sys.executable, str(CHECK), "--invariants"]))
        else:
            # test id lines, optionally with a parenthesised description, e.g.
            # "C30-01 (golden path)" or "X01-01, X02-01"
            for tid in [t.strip() for t in item.replace(",", " ").split()]:
                if tid.endswith("-01"):
                    steps.append(("test", tid, [sys.executable, str(TESTS / (tid.lower() + ".py"))]))
    return steps


def main():
    if not JOB.is_file():
        return emit(ID, "FAIL", "integration job definition missing")
    job = json.loads(JOB.read_text(encoding="utf-8"))
    steps = expand_run_order(job)
    if not steps:
        return emit(ID, "FAIL", "integration job has no executable steps")

    log_lines = [
        "X04 integration run",
        "run_order=%d steps" % len(steps),
        "pass_rule=%s" % job.get("pass_rule", "UNDECLARED"),
        "",
    ]
    failed = []

    # consume assemble_from: the job must actually inspect the artefacts it
    # claims to assemble. Missing product dirs are reported, not hidden.
    assembled, absent = [], []
    for pattern in job.get("assemble_from", []):
        matches = sorted(PROJECT_ROOT.glob(pattern))
        (assembled if matches else absent).append(
            "%s(%d)" % (pattern, len(matches)))
    log_lines.append("ASSEMBLE present=%s" % (", ".join(assembled) or "none"))
    log_lines.append("ASSEMBLE absent =%s" % (", ".join(absent) or "none"))
    log_lines.append("")

    for kind, label, cmd in steps:
        if cmd is None:
            failed.append("%s (unknown step form)" % label)
            log_lines.append("STEP %s  UNKNOWN" % label)
            continue
        code, out = run_step(cmd, PROJECT_ROOT)
        sts = statuses(out)
        non_green = [(tid, s) for tid, s in sts if s != "PASS"]
        ok = code == 0 and not non_green
        log_lines.append("STEP %s  exit=%d  %s" % (label, code, "OK" if ok else "NOT_GREEN"))
        if out:
            for line in out.splitlines():
                log_lines.append("    " + line)
        if not ok:
            failed.append("%s (exit=%d, non_green=%s)" % (label, code, non_green or "none"))
        log_lines.append("")

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    if failed:
        return emit(ID, "FAIL", "%d/%d steps not green: %s | log=%s" % (
            len(failed), len(steps), "; ".join(failed), LOG.relative_to(PROJECT_ROOT)))
    return emit(ID, "PASS", "all %d steps green | log=%s" % (
        len(steps), LOG.relative_to(PROJECT_ROOT)))


if __name__ == "__main__":
    sys.exit(main())
