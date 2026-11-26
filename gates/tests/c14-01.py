"""C14-01: 兑换系统使用统一数值词汇表。

SPEC: vocab/ 中每个条目含 id / cost / effect / kind 四字段；id 全局唯一；
      结算清单引用的 ID 必须命中词汇表；兑换点变动与 cost 一致；
      词汇表之外的 effect 字符串一律拒绝。
BLOCKER: P4 词汇表与兑换接口未实现。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit

ID = "C14-01"


def main():
    vocab = ROOT / "vocab" / "exchange.json"
    if not vocab.is_file():
        return emit(ID, "FAIL", "vocab/exchange.json missing; P4 not implemented")
    rows = json.loads(vocab.read_text(encoding="utf-8"))
    ids = [r.get("id") for r in rows]
    if len(ids) != len(set(ids)) or any(x is None for x in ids):
        return emit(ID, "FAIL", "vocabulary ids not unique or missing")
    return emit(ID, "FAIL", "cost/effect assertion needs exchange implementation; expected red phase")


if __name__ == "__main__":
    sys.exit(main())
