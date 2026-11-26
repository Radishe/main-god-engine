# 通用夹具 F1~F6（00 §1）

本目录是 00 文件 §1 定义的实体夹具，维护者所有，各包只读。

| 文件 | 夹具 | 用途 |
| :--- | :--- | :--- |
| `f1-instance-a.json` | F1 副本 A（战斗） | 属性轴 hp/atk/def；1 个事件改变 hp |
| `f2-instance-b.json` | F2 副本 B（生存） | 属性轴 health/hunger；1 个事件改变 hunger |
| `f3-ledger.json` | F3 初始账本 | 轮回者 R-0001，兑换点 1000（结构测试整数），空能力/物品，未永久死亡 |
| `f4-settlement.json` | F4 合法结算清单 | `credit_delta=137` 是结构测试整数，非玩法数值 |
| `f6-malicious.py` | F6 恶意副本 | `run(ledger_view)` 尝试直写 `credits`，必须被拒 |

F5 的 6 个非法变体尚未落成实体文件（属 S4 validation CLI，由 P2 负责）。

**纪律**：夹具只描述结构、不含玩法数值；`$comment` 一类元数据放在本文件，不混入账本/清单 JSON，否则会污染深度相等断言。
