# 无限流 · 主神框架

> **一个开源众创的无限流题材游戏框架**：把「主神」做成开源的规则与状态引擎，把剧本做成社区可贡献的数据。
> 框架上传 GitHub，让所有人为它填充副本剧本——各种世界观、各种玩法、各种呈现形式并存，收敛到同一套主神规则之下。

---

## 为什么要先做「硬框架」

社区众创的前提是：**副本作者碰不到主神的规则**。否则每个剧本自带一套私有规则，框架会迅速失控。

所以本项目先把边界钉死：

- **主神** = 唯一的规则与状态引擎，持有轮回者状态、结算权、账本持久化权。
- **副本** = 纯数据声明，只描述「这里有什么、发生什么」，结束时只交一份**标准化结算清单**。
- **收益换算、汇率、跨副本平衡**全部由主神层控制，副本作者不需要知道。

只要异构副本能无缝切换、且主神账本不被污染，架构就成立——这条已用两个形态完全不同的副本验证通过。

---

## 当前状态：地基已完成，可以开放贡献

| 地基 | 状态 |
| :--- | :--- |
| 规则决议台账（D1~D24） | 闭环，无待拍板项 |
| 主神引擎原型（Python） | 可跑：申报 → 公证 → 结算 → 账本落定 |
| 结算接口 + Schema + validation CLI | 社区众创的命门，已扎实 |
| 异构副本验证 | D1 / D2 全链通过，账本零污染 |
| 门禁 + CI + 治理（CODEOWNERS、gate-approved） | 生效，防作弊、防倒退 |

**下一步**：按愿景本来就该开放社区贡献副本了。地基已稳，往接口上追加配置即可，不需要重新设计。

---

## 给副本作者（想贡献剧本）

1. 先读 [`docs/SCHEMA.md`](docs/SCHEMA.md)——声明式副本与结算清单的字段契约。
2. 参考现成副本 [`content/instances/D1`](content/instances/D1)、[`content/instances/D2`](content/instances/D2)。
3. 提交前用 `python tools/validate.py <你的结算清单.json>` 自检，退出码 0 才算合规。
4. 贡献流程见 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)；审核标准见 [`docs/REVIEW.md`](docs/REVIEW.md)。

**红线**：副本只能交数据，不能含 `settle()`、账本写入、引擎导入；未知场景标签、字段集扩展都会被拒。

---

## 给维护者（规则与门禁）

- **设计结论与历史**：[`docs/设计决议记录.md`](docs/设计决议记录.md)（D1~D24，含被推翻设定）、[`docs/技术债与盲点.md`](docs/技术债与盲点.md)。
- **文档导航**：[`docs/README.md`](docs/README.md)。
- **门禁系统怎么运作、怎么复用**：[`docs/GATES-门禁系统手册.md`](docs/GATES-门禁系统手册.md)。
- **验收契约**：[`docs/00-阶段与验收标准.md`](docs/00-阶段与验收标准.md)，判定权在 `gates/manifest.json` + `gates/check.py`，退出码即判定。

自检常用：

```bash
python gates/check.py --run           # 全量红绿
python gates/check.py --baseline      # 绿线棘轮（CI 合入判据）
python gates/check.py --coverage      # HANDOFF: READY = 可放手
python tools/validate.py gates/fixtures/f4-settlement.json
```

CI 在每次 PR 跑 coverage / baseline ratchet / invariants 与结算清单校验；改裁判面（`gates/`、`.github/`、`config/`、`docs/设计决议记录.md`）需 `gate-approved` 标签，见 [`.github/CODEOWNERS`](.github/CODEOWNERS)。

验收证据由测试运行时生成、纳入版本历史，见 `evidence/`（S0~S4、sc、int、content 各阶段）。CI 可复现性的日志路径登记于 `evidence/s4/g1-03.txt`（S4-G1-03 要求此路径在 README 可查）。

---

## 一句话

**把主神做成开源引擎，把剧本做成社区数据，用一条不可越界的结算接口让两者安全共存。** 地基已打完，众创可以开始。
