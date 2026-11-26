"""P4 变异检查：在临时副本上把 src/notary/exchange.py 改坏，验证包内自检由绿转红再转绿，
并把真实运行输出写入 evidence/p4/mutation.log（不手写假 PASS 日志）。

Run: python tests/p4/mutation_check.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
LOG = ROOT / "evidence" / "p4" / "mutation.log"
TARGET = "src/notary/exchange.py"
GUARD = "tests/p4/exchange_check.py"

RECIPES = [
    {
        "id": "payout_off_by_one",
        "original": '    return entry.get("cost")',
        "mutant": '    return entry.get("cost") + 1',
        "note": "payout 不再等于 cost，破坏『兑换点变动与 cost 一致』",
    },
    {
        "id": "unknown_effect_accepted",
        "original": "    return isinstance(effect, str) and effect in known_effects()",
        "mutant": "    return True",
        "note": "词表外 effect 不再被拒绝",
    },
    {
        "id": "unknown_id_resolves",
        "original": (
            "    for entry in all_entries():\n"
            "        if entry.get(\"id\") == item_id:\n"
            "            return entry\n"
            "    return None"
        ),
        "mutant": (
            "    for entry in all_entries():\n"
            "        if entry.get(\"id\") == item_id:\n"
            "            return entry\n"
            "    return {\"id\": item_id, \"cost\": 1, \"effect\": \"structural_placeholder\", \"kind\": \"item\", \"enabled_in\": []}"
        ),
        "note": "未登记 ID 被伪造命中，破坏 I5",
    },
]


def run_guard(guard_path, cwd):
    proc = subprocess.run(
        [PY, str(guard_path)], cwd=str(cwd),
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    lines = [l for l in (proc.stdout or "").splitlines() if l.startswith("TEST ")]
    line = lines[0] if len(lines) == 1 else "no single TEST line (exit=%d)" % proc.returncode
    parts = line.split(" ", 3)
    status = parts[2] if len(parts) > 2 else "BAD"
    if status == "PASS" and proc.returncode != 0:
        status = "CONTRADICTION"
    return proc.returncode, line, status


def build_sandbox(sandbox):
    """复制接口运行所需的最小子树；guard 的 ROOT=parents[2] 指向 sandbox 根。"""
    for rel in (
        "src/notary/__init__.py",
        TARGET,
        "gates/stubs/notary.json",
        "gates/stubs/vocabulary.json",
        "vocab/items.json",
        "vocab/abilities.json",
        "vocab/exchange.json",
        GUARD,
    ):
        src, dst = ROOT / rel, sandbox / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def mutate_case(recipe):
    lines = []
    with tempfile.TemporaryDirectory(prefix="p4-mutation-") as tmp:
        sandbox = Path(tmp)
        build_sandbox(sandbox)
        target = sandbox / TARGET
        source = target.read_text(encoding="utf-8")
        if recipe["original"] not in source:
            return ["%s: SKIP stale anchor (original not found)" % recipe["id"]], False

        guard = sandbox / GUARD
        base_code, base_line, base_status = run_guard(guard, sandbox)
        lines.append("%s: baseline %s (exit=%d)" % (recipe["id"], base_line, base_code))
        try:
            target.write_text(
                source.replace(recipe["original"], recipe["mutant"], 1),
                encoding="utf-8",
            )
            mut_code, mut_line, mut_status = run_guard(guard, sandbox)
        finally:
            target.write_text(source, encoding="utf-8")
        lines.append("mutant(%s): %s (exit=%d)  # %s" % (
            recipe["id"], mut_line, mut_code, recipe["note"]))
        caught = base_status == "PASS" and mut_status == "FAIL"
        lines.append("RESULT: %s" % ("green -> red  MUTATION_CAUGHT" if caught
                                     else "MUTATION_NOT_CAUGHT"))
        rest_code, rest_line, rest_status = run_guard(guard, sandbox)
        lines.append("restored: %s (exit=%d)" % (rest_line, rest_code))
        lines.append("RESTORE: %s" % ("OK" if rest_status == "PASS" else "FAILED"))
        return lines, caught and rest_status == "PASS"


def main():
    all_lines = ["P4 mutation check (src/notary/exchange.py; replayed on temporary copies)", ""]
    all_ok = True
    for recipe in RECIPES:
        lines, ok = mutate_case(recipe)
        all_lines.extend(lines)
        all_lines.append("")
        all_ok = all_ok and ok
    all_lines.append("OVERALL: %s" % ("ALL_MUTATIONS_CAUGHT" if all_ok else "SOME_MUTATIONS_ESCAPED"))

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    print("\n".join(all_lines))
    print("evidence written: %s" % LOG.relative_to(ROOT))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
