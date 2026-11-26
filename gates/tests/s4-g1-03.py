"""S4-G1-03: CI reproducibility of the validation CLI (00 §7).

Checks the committed CI configuration — NOT a live CI run:
  - a job step runs the validation CLI (from config/paths.json);
  - that step is blocking (no continue-on-error on it);
  - the log path is registered in README.

MAINTAINER-OWNED: the assertion target is .github/workflows (protected), so a
P2 implementation agent cannot and must not edit this test or the workflow.
The CLI itself is still P2's job (S4-G1-01); this test only verifies the CI
wiring around it, which is the maintainer's side of the handoff.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G1-03"
EXPECTED_LOG = "evidence/s4/g1-03.txt"


def main():
    paths = ROOT / "config" / "paths.json"
    if not paths.is_file():
        return emit(ID, "FAIL", "config/paths.json missing")
    cli = json.loads(paths.read_text(encoding="utf-8")).get("validation_cli")
    if not cli:
        return emit(ID, "FAIL", "validation_cli not registered in paths.json")

    wf = ROOT / ".github" / "workflows" / "gates.yml"
    if not wf.is_file():
        return emit(ID, "PENDING", "workflow not present")
    text = wf.read_text(encoding="utf-8")

    # a step must invoke the CLI (accept either python <cli> or the bare path)
    invoked = cli in text or ("python" in text and cli in text)
    if not invoked:
        return emit(ID, "FAIL", "CI never runs validation CLI (%s)" % cli)

    # the CLI step must be blocking: no continue-on-error in its run block
    lines = text.splitlines()
    run_line = next((i for i, l in enumerate(lines) if cli in l), None)
    if run_line is None:
        return emit(ID, "FAIL", "CLI run step not located")
    block = "\n".join(lines[max(0, run_line - 2): run_line + 3])
    if "continue-on-error" in block:
        return emit(ID, "FAIL", "validation CLI step is non-blocking")

    readme = ROOT / "README.md"
    if not readme.is_file() or EXPECTED_LOG not in readme.read_text(encoding="utf-8"):
        return emit(ID, "FAIL", "log path %s not registered in README" % EXPECTED_LOG)

    ev = ROOT / "evidence" / "s4"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-03.txt").write_text(
        "cli=%s\nstep=blocking\nlog_registered=%s\n" % (cli, EXPECTED_LOG), encoding="utf-8")
    return emit(ID, "PASS", "CI runs %s as blocking step; log path registered" % cli)


if __name__ == "__main__":
    sys.exit(main())
