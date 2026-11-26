"""C13-01: 跨副本持久化 — A 落账后 B 读到连续账本。

SPEC: 副本 A 落账后加载副本 B，B 的入场快照等于落账后的账本；
      A 的属性轴键不得出现在 B 的快照中；入场公证三步标记齐全；
      最终账本逐字段可复算。词汇表 enabled_in 的完整生效规则由 X04 复验。
MODE: 包级自检使用 fake_settle + fake_notary（2026-11-12 拍板），P4 不等 P1/P3。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit
sys.path.insert(0, str(ROOT / "gates" / "stubs"))
from fake_settle import settle
from fake_notary import admit, assert_steps_complete

ID = "C13-01"


def main():
    registry = {"sword", "fireball"}
    ledger = {"reincarnator_id": "r1", "credits": 0, "items": []}
    manifest_a = {
        "instance_id": "A",
        "reincarnator_id": "r1",
        "completion": "success",
        "credit_delta": 5,
        "ability_ids": ["fireball"],
        "item_ids": ["sword"],
    }
    after = settle(ledger, manifest_a, registry=registry)
    ok, markers, snapshot = admit(
        {"axes": ["health", "hunger"], "asset_ids": []}, after
    )
    leaked = [k for k in ("hp", "atk", "def") if k in (snapshot or {})]
    good = (ok and assert_steps_complete(markers)
            and snapshot == after and not leaked
            and after["credits"] == ledger["credits"] + 5)
    return emit(ID, "PASS" if good else "FAIL",
                "via fake_settle+fake_notary: snapshot continuity; X04 integration still required")


if __name__ == "__main__":
    sys.exit(main())
