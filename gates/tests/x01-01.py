"""X01-01: 阶段交接 — S1 账本 -> S2 入场快照。

SPEC: S1 结束时的 ledger.json 与 S2 首个副本的 snapshot.json 字段集相同、值深度相等；
      S2 不得引入 S1 未登记的账本字段；轮回者 ID 在交接前后保持一致。
      这是「阶段之间状态不丢失」的唯一断言，不属于任何单阶段。
BLOCKER: S1 / S2 产物均未落地。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "X01-01"


def main():
    s1 = ROOT / "evidence" / "s1" / "final_ledger.json"
    s2 = ROOT / "evidence" / "s2" / "first_snapshot.json"
    if not (s1.is_file() and s2.is_file()):
        return emit(ID, "PENDING", "stage handoff artefacts not produced yet")
    return emit(ID, "FAIL", "cross-stage deep-equality assertion needs runner; expected red phase")


if __name__ == "__main__":
    sys.exit(main())
