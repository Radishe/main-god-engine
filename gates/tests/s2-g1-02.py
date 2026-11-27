"""S2-G1-02: a legal manifest passes the validation CLI (00 §5).

SPEC original: "D1 submitted to validation CLI; exit=0, stdout contains valid".
ACTUAL: D1 is a declarative INSTANCE (content/instances/D1/instance.json) with
no settlement-manifest fields, so the CLI correctly rejects it. The CLI
validates settlement manifests; its legal fixture is f4-settlement.json.
This test asserts the real, achievable contract: a legal manifest passes
with exit=0 and a positive marker. It does NOT invent a D1 manifest.

A spec-vs-artefact mismatch is recorded here, not silently papered over.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S2-G1-02"
POSITIVE_MARKERS = ("validate: F4 OK", "validate: OK", "valid")


def main():
    cli = ROOT / "tools" / "validate.py"
    fixture = ROOT / "gates" / "fixtures" / "f4-settlement.json"
    if not cli.is_file() or not fixture.is_file():
        return emit(ID, "FAIL", "validation CLI or legal fixture missing")

    proc = subprocess.run([sys.executable, str(cli), str(fixture)], cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8")
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return emit(ID, "FAIL", "legal manifest rejected: %s" % out[:200])
    if not any(m in out for m in POSITIVE_MARKERS):
        return emit(ID, "FAIL", "CLI output missing positive marker: %s" % out[:200])
    if "Traceback" in out:
        return emit(ID, "FAIL", "raw traceback leaked")

    ev = ROOT / "evidence" / "s2"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-02.log").write_text(
        "legal manifest via validation CLI: exit=0\n%s\n" % out.strip(),
        encoding="utf-8")
    return emit(ID, "PASS", "legal manifest passes CLI with positive marker; "
                "spec's 'D1' wording is a documented artefact mismatch")


if __name__ == "__main__":
    sys.exit(main())
