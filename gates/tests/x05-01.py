"""X05-01: mutation evidence must be REPRODUCIBLE, not a trusted log.

The audit found that a hand-written mutation.log could forge PASS/FAIL/PASS.
This test does NOT trust logs. It reads gates/mutation_recipes.json (maintainer-
owned), replays each recipe on a TEMPORARY COPY of the source tree, and verifies
the guard test actually flips green -> red -> green. A forged log is irrelevant;
only a real, replayable mutation counts.

A package with no recipes is DEFERRED (never silently PASS).
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "X05-01"
RECIPES = ROOT / "gates" / "mutation_recipes.json"


def _run_guard(test_path, cwd):
    """Run a guard script located in the temp copy, with its own ROOT."""
    try:
        proc = subprocess.run([sys.executable, str(test_path)], cwd=str(cwd),
                              capture_output=True, text=True, encoding="utf-8", timeout=30)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", ""
    lines = [l for l in (proc.stdout or "").splitlines() if l.startswith("TEST ")]
    if len(lines) != 1:
        return "BAD_OUTPUT", "%d TEST lines" % len(lines)
    parts = lines[0].split(" ", 3)
    status = parts[2] if len(parts) > 2 else "BAD"
    # status + exit code must agree (same strict rule as check.py judge_test)
    if status == "PASS" and proc.returncode != 0:
        return "CONTRADICTION", "PASS with exit=%d" % proc.returncode
    return status, lines[0]


def replay(recipe, sandbox):
    """Apply one recipe on the temp copy; return (ok, detail)."""
    target = sandbox / recipe["target"]
    guard = sandbox / "gates" / "tests" / (recipe["guard"] + ".py")
    if not target.is_file() or not guard.is_file():
        return False, "target or guard missing in sandbox"
    original = target.read_text(encoding="utf-8")
    if recipe["original"] not in original:
        return False, "recipe original snippet not found (stale recipe)"
    if recipe["original"] == recipe["mutant"]:
        return False, "mutant identical to original"

    base, base_line = _run_guard(guard, sandbox)
    try:
        target.write_text(original.replace(recipe["original"], recipe["mutant"], 1),
                          encoding="utf-8")
        mutant, mut_line = _run_guard(guard, sandbox)
    finally:
        target.write_text(original, encoding="utf-8")
    restored, _ = _run_guard(guard, sandbox)

    ok = base == "PASS" and mutant == "FAIL" and restored == "PASS"
    return ok, "%s base=%s mutant=%s restored=%s" % (
        recipe["id"], base, mutant, restored)


def main():
    if not RECIPES.is_file():
        return emit(ID, "DEFERRED", "mutation_recipes.json missing; no package claims reproducible mutation")
    recipes = json.loads(RECIPES.read_text(encoding="utf-8")).get("recipes", [])
    if not recipes:
        return emit(ID, "DEFERRED", "no mutation recipes registered")

    # Build a temporary copy of only what the guards need: src/ + gates/tests/.
    # common.ROOT = parents[2] of the test file, so a copied test in
    # <sandbox>/gates/tests/ resolves to <sandbox> and imports <sandbox>/src.
    with tempfile.TemporaryDirectory(prefix="x05-replay-") as tmp:
        sandbox = Path(tmp)
        (sandbox / "gates" / "tests").mkdir(parents=True)
        shutil.copytree(ROOT / "src", sandbox / "src")
        for f in (ROOT / "gates" / "tests").glob("*.py"):
            shutil.copy2(f, sandbox / "gates" / "tests" / f.name)
        # guards read config/ and gates/fixtures/ relative to ROOT; copy those too
        if (ROOT / "config").is_dir():
            shutil.copytree(ROOT / "config", sandbox / "config")
        if (ROOT / "gates" / "fixtures").is_dir():
            shutil.copytree(ROOT / "gates" / "fixtures", sandbox / "gates" / "fixtures")
        if (ROOT / "gates" / "stubs").is_dir():
            shutil.copytree(ROOT / "gates" / "stubs", sandbox / "gates" / "stubs")
        # C30 golden path loads instances from content/ and IDs from vocab/
        for sub in ("content", "vocab"):
            if (ROOT / sub).is_dir():
                shutil.copytree(ROOT / sub, sandbox / sub)

        results = [replay(r, sandbox) for r in recipes]

    bad = ["%s (%s)" % (r["id"], detail) for r, (ok, detail) in zip(recipes, results) if not ok]
    if bad:
        return emit(ID, "FAIL", "replay failed: " + " | ".join(bad))
    detail = " | ".join("%s %s" % (r["id"], d) for r, (_, d) in zip(recipes, results))
    return emit(ID, "PASS", "%d recipe(s) replayed green->red->green: %s" % (len(recipes), detail))


if __name__ == "__main__":
    sys.exit(main())
