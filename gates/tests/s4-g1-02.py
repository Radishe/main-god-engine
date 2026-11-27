"""S4-G1-02: legal manifests pass the validation CLI (00 §7).

SPEC original: "F4 + S2's D1 / D2, three commands all exit=0".
ACTUAL: D1 is a declarative instance (no settlement-manifest fields) and D2
is a human-in-loop artefact not yet produced — neither is a legal manifest.
This test asserts the achievable contract over the legal manifests that DO
exist (F4 fixture + P2's F4-legal fixture) and records the mismatch rather
than inventing D1/D2 manifests.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "S4-G1-02"
FIXTURES = ["gates/fixtures/f4-settlement.json", "tests/p2/fixtures/F4-legal.json"]


def main():
    cli = ROOT / "tools" / "validate.py"
    if not cli.is_file():
        return emit(ID, "FAIL", "validation CLI missing")
    problems = []
    for rel in FIXTURES:
        fx = ROOT / rel
        if not fx.is_file():
            problems.append("%s missing" % rel)
            continue
        proc = subprocess.run([sys.executable, str(cli), str(fx)], cwd=str(ROOT),
                              capture_output=True, text=True, encoding="utf-8")
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            problems.append("%s rejected: %s" % (rel, out[:120]))
        elif "Traceback" in out:
            problems.append("%s leaked traceback" % rel)
    if problems:
        return emit(ID, "FAIL", "; ".join(problems))

    ev = ROOT / "evidence" / "s4"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "g1-02.log").write_text(
        "\n".join("%s: exit=0" % f for f in FIXTURES) +
        "\nnote: spec's D1/D2 are not manifests (D1 declarative, D2 human-in-loop); not fabricated\n",
        encoding="utf-8")
    return emit(ID, "PASS", "%d legal manifests pass CLI (D1/D2 mismatch documented)" % len(FIXTURES))


if __name__ == "__main__":
    sys.exit(main())
