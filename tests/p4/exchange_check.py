"""P4 包内自检：src/notary/exchange.py 纯函数接口（门禁只收 gates/tests/*.py，此处不自动执行）。

覆盖 C14 五条规格：字段齐全 / id 唯一 / 清单引用命中 / payout 与 cost 一致 / 词表外 effect 拒绝。
输出遵循项目协议：TEST <ID> <PASS|FAIL> <reason>，退出码 PASS=0 / FAIL=1。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.notary.exchange import (
    all_entries,
    duplicate_ids,
    exchange_entries,
    is_known_effect,
    is_well_formed,
    known_effects,
    lookup,
    payout_for,
)

ID = "P4-EXCH-01"


def main():
    rows = all_entries()
    if not rows:
        print("TEST %s FAIL empty vocabulary" % ID)
        return 1

    # 1) 每条含 id/cost/effect/kind（stub 另要求 enabled_in，kind 为枚举）
    if not all(is_well_formed(e) for e in rows):
        print("TEST %s FAIL malformed entry (missing field or bad kind)" % ID)
        return 1

    # 2) id 全局唯一（跨 items / abilities / exchange 全部来源）
    if duplicate_ids():
        print("TEST %s FAIL duplicate ids: %s" % (ID, duplicate_ids()))
        return 1

    # 3) 结算清单引用的 id 必须命中词汇表（I5）
    manifest_ids = ["exchange/standard", "item/bandage", "ability/combat_instinct"]
    if any(lookup(i) is None for i in manifest_ids):
        print("TEST %s FAIL manifest id not in vocabulary" % ID)
        return 1
    if lookup("unregistered_item") is not None:
        print("TEST %s FAIL unknown id unexpectedly resolved" % ID)
        return 1

    # 4) 兑换点变动与 cost 一致：payout 原样返回结构占位 cost，不发明价目
    for entry in rows:
        if payout_for(entry["id"]) != entry["cost"]:
            print("TEST %s FAIL payout != cost for %s" % (ID, entry["id"]))
            return 1
    if payout_for("unregistered_item") is not None:
        print("TEST %s FAIL payout for unknown id must be None" % ID)
        return 1

    # 5) 词汇表之外的 effect 一律拒绝
    if not is_known_effect("structural_placeholder"):
        print("TEST %s FAIL registered effect rejected" % ID)
        return 1
    if is_known_effect("structural_placeholder") and "structural_placeholder" not in known_effects():
        print("TEST %s FAIL known_effects inconsistent" % ID)
        return 1
    for bad in ("free_gold", "", None, 123):
        if is_known_effect(bad):
            print("TEST %s FAIL out-of-vocab effect accepted: %r" % (ID, bad))
            return 1

    if not exchange_entries():
        print("TEST %s FAIL exchange.json contributed no entries" % ID)
        return 1

    print("TEST %s PASS %d entries well-formed, ids unique, effects validated, payout==cost (structural placeholder)" % (ID, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
