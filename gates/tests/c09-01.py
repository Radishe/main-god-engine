"""C09-01: 产物公证 — 未公证物品/能力不能带出副本。

SPEC: 结算清单 item_ids / ability_ids 中每个 ID 必须存在于词汇表；
      出现未注册 ID 时 settle() 必须拒绝，且账本 SHA-256 不变；
      拒绝原因含 rejected_unnotarized 与具体 ID。
MODE: 包级自检使用契约替身 fake_settle（2026-11-12 拍板），因此 P4 不必等 P1。
      真实 settle() 的正确性由 X04-01 / C30-01 集成门禁复验，两者不互相替代。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit
sys.path.insert(0, str(ROOT / "gates" / "stubs"))
from fake_settle import settle, Rejected

ID = "C09-01"


def main():
    ledger = {"reincarnator_id": "r1", "credits": 0, "items": []}
    before = json.dumps(ledger, sort_keys=True)
    manifest = {
        "instance_id": "i1",
        "reincarnator_id": "r1",
        "completion": "success",
        "credit_delta": 10,
        "ability_ids": [],
        "item_ids": ["unregistered_item"],
    }
    try:
        settle(ledger, manifest, registry={"registered_item"})
    except Rejected as exc:
        unchanged = json.dumps(ledger, sort_keys=True) == before
        ok = "rejected_unnotarized" in str(exc) and unchanged
        return emit(ID, "PASS" if ok else "FAIL",
                    "via fake_settle: %s; X04 integration still required" % exc)
    return emit(ID, "FAIL", "via fake_settle: unregistered id was not rejected")


if __name__ == "__main__":
    sys.exit(main())
