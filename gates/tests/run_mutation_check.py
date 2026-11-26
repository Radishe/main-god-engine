"""Mutation runner: apply each recipe in gates/mutation_recipes.json to the REAL
source, verify the guard flips green->red->green, then restore.

This is the developer-facing tool that regenerates evidence/p1/mutation.log for
human inspection. X05-01 does NOT trust that log; it replays the same recipes on
a temporary copy. Recipes are the single source of truth for both.

Run: python gates/tests/run_mutation_check.py
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
RECIPES = ROOT / "gates" / "mutation_recipes.json"
LOG = ROOT / "evidence" / "p1" / "mutation.log"


def run(test):
    proc = subprocess.run([PY, str(ROOT / "gates" / "tests" / (test + ".py"))],
                          capture_output=True, text=True, encoding="utf-8", timeout=30)
    for line in (proc.stdout or "").splitlines():
        if line.startswith("TEST "):
            return proc.returncode, line
    return proc.returncode, "%s produced no TEST line" % test


def mutate_case(recipe):
    name, test, rel = recipe["id"], recipe["guard"], recipe["target"]
    target = ROOT / rel
    if not target.is_file():
        return ["%s: SKIP target missing" % name], False
    source = target.read_text(encoding="utf-8")
    if recipe["original"] not in source:
        return ["%s: SKIP original snippet not found (stale recipe)" % name], False
    base_code, base_line = run(test)
    lines = ["%s: baseline %s (exit=%d)" % (name, base_line, base_code)]
    caught = False
    try:
        target.write_text(source.replace(recipe["original"], recipe["mutant"], 1),
                          encoding="utf-8")
        mut_code, mut_line = run(test)
        lines.append("mutant(%s): %s (exit=%d)" % (name, mut_line, mut_code))
        caught = base_code == 0 and mut_code != 0
        lines.append("RESULT: %s" % ("green -> red  MUTATION_CAUGHT" if caught
                                     else "MUTATION_NOT_CAUGHT"))
    finally:
        target.write_text(source, encoding="utf-8")
    rest_code, rest_line = run(test)
    lines.append("restored: %s (exit=%d)" % (rest_line, rest_code))
    lines.append("RESTORE: %s" % ("OK" if rest_code == 0 else "FAILED"))
    return lines, caught and rest_code == 0


def main():
    if not RECIPES.is_file():
        print("ERROR: %s missing" % RECIPES.name)
        return 1
    recipes = json.loads(RECIPES.read_text(encoding="utf-8")).get("recipes", [])
    all_lines = ["P1 mutation check (from recipes; X05-01 replays independently)", ""]
    all_ok = True
    for recipe in recipes:
        lines, ok = mutate_case(recipe)
        all_lines.extend(lines)
        all_lines.append("")
        all_ok = all_ok and ok

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    print("\n".join(all_lines))
    print("OVERALL: %s" % ("ALL_MUTATIONS_CAUGHT" if all_ok else "SOME_MUTATIONS_ESCAPED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
