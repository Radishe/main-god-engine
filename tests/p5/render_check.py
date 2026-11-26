"""P5 包内自检：真实调用 src.render 解析器，产出 evidence/p5/mutation.log。

本脚本不在 gates/tests/ 下，门禁不会自动执行；它只负责用真实实现跑一次
可追溯的 render_profile 解析记录（不是门禁判定，也不伪造任何测试 PASS）。
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import src.render as render

STUB = json.loads((ROOT / "gates" / "stubs" / "loader.json").read_text(encoding="utf-8"))
EXPECTED = tuple(STUB["render_profile"]["values"])
LOG_PATH = ROOT / "evidence" / "p5" / "mutation.log"


def main():
    lines = ["P5 render_profile resolver run @ %s" % datetime.now(timezone.utc).isoformat()]
    lines.append("mode=metadata_placeholder affects_settlement=%s" % render.affects_settlement())

    known = render.known_profiles()
    lines.append("contract_values=%s" % (list(EXPECTED),))
    lines.append("registered_values=%s" % (list(known),))
    lines.append("contract_match=%s" % (known == EXPECTED))

    resolved = 0
    for profile in EXPECTED:
        meta = render.resolve(profile)
        if meta is None:
            lines.append("resolve(%s) -> None (UNRESOLVED)" % profile)
            continue
        resolved += 1
        lines.append("resolve(%s) -> %s" % (profile, render.describe(profile)))
        lines.append("  metadata_fields=%s" % sorted(meta.keys()))

    unknown = "not_a_profile"
    lines.append("resolve(%s) -> %s" % (unknown, render.resolve(unknown)))

    inst = {"render_profile": EXPECTED[0]}
    via_instance = render.resolve_instance(inst)
    lines.append("resolve_instance(%s) -> pipeline=%s" % (inst, via_instance["pipeline"]))

    first = render.resolve(EXPECTED[0])
    first["presentation"]["projection"] = "mutated_by_caller"
    isolated = render.resolve(EXPECTED[0])["presentation"]["projection"] != "mutated_by_caller"
    lines.append("copy_isolation=%s" % isolated)

    lines.append("summary: %d/%d profiles resolved; affects_settlement=%s; copy_isolation=%s" % (
        resolved, len(EXPECTED), render.affects_settlement(), isolated))

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    ok = (resolved == len(EXPECTED) and known == EXPECTED
          and render.affects_settlement() is False and isolated)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
