# 无限流主神规则引擎（Python 原型）

社区副本 + 主神唯一账本的规则引擎原型。设计文档见 `docs/`，验收契约见 `gates/`。

## 门禁与证据

CI 在每次 PR 执行 `gates/check.py` 的 coverage / baseline ratchet / invariants，
并运行 `tools/validate.py`（结算清单校验，S4-G1-03 要求为 blocking 步骤）。
合规改动需 `gate-approved` 标签；裁判面路径见 `.github/CODEOWNERS`。

验收证据（测试运行时生成，纳入版本历史）：

| 证据 | 内容 |
| :--- | :--- |
| `evidence/s4/g1-03.txt` | S4-G1-03 CI 可复现性：CLI 为 blocking 步骤、日志路径登记 |
| `evidence/s1/` | S1 阶段各验收（轴字面量扫描、加轴 diff、去重、快照隔离等） |
| `evidence/sc/` | sc 阶段入场公证与 import guard |
| `evidence/int/` | X03 回归日志、X04 集成日志 |

详见 `docs/00-阶段与验收标准.md`。
