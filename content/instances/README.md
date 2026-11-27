# 副本作者最小模板

> 一页纸讲清「写一个能被主神接受的副本」需要什么。只看本页 + 上级 `README.md` 的「给副本作者」即可，不必读引擎源码。
> 真正的字段契约在 [`../../docs/SCHEMA.md`](../../docs/SCHEMA.md)；本页是它的作者速查版，不另立规则。

## 先记住一条顺序

**先落 `instance.json`（副本声明），再写 `settlement.json`（结算清单）。** CLI 会检查 `instance_id` 是否命中一个已落盘的 `content/instances/*/instance.json`——没有声明就交清单，必被拒。

每个副本是 `content/instances/<ID>/` 下的两个文件：

```
content/instances/MY_STORY/
├── instance.json      # 副本里有什么、发生什么（纯数据）
└── settlement.json    # 结束时交给主神的清单
```

`instance.json` 的 `instance_id` 与 `settlement.json` 的 `instance_id` 必须**完全一致**。

---

## `instance.json` 字段

| 字段 | 约束 |
| :--- | :--- |
| `instance_id` | string，唯一，须与目录名/清单一致；先落盘 |
| `instance_type` | string，自由文本（如 `combat`/`exploration`/`contract_negotiation`），无枚举 |
| `axes` | `{名称: 整数}`。名称由副本自定，引擎不关心叫什么；值必须是整数 |
| `events` | `[{tick:整数, kind:string, axis:已在 axes 声明的名称, delta:整数, label:string}]` |
| `render_profile` | 枚举 `3d` / `2d_flat` / `graffiti`（见 `gates/stubs/loader.json`）；不影响结算 |
| `asset_ids` | `[string]`，须命中主神公证资产库，否则入场公证被拒；可为空 |
| `scene_tag` | 可选，枚举 `peaceful` / `raid` / `contract`；目前是**声明性元数据**，不改收益 |
| `settlement_evidence` | `{volume: 整数, completion_basis: string}`；`volume` 即理论最高分 |
| `$comment` | ✅ **只有 instance.json 可以放** |

**禁止**：声明里不得含引擎导入令牌（`from src.core` / `import src.core` / `from core.` / `import ledger` / `from src.notary` / `import src.notary`，唯一真源 `gates/stubs/forbidden_imports.json`）。命中即 `rejected_import`。不得含 `settle()`、账本写入、惩罚逻辑——副本是数据，不是代码。

---

## `settlement.json` 字段（冻结字段集，多一个键都不行）

| 字段 | 必填 | 约束 |
| :--- | :--- | :--- |
| `instance_id` | ✅ | 须命中已落盘的实例 |
| `reincarnator_id` | ✅ | string（示例 `R-0001`） |
| `completion` | ✅ | 枚举 **`success` / `failure` / `aborted`** |
| `credit_delta` | ✅ | 整数。带 `claims` 时**必须为 0**，否则 `rejected_double_report` |
| `ability_ids` | ✅ | `[string]`，不可重复；每个须命中公证词汇表且 `enabled_in` 含本 `instance_id` |
| `item_ids` | ✅ | `[string]`，不可重复；每个须命中公证词汇表 |
| `idempotency_key` | 否 | string，用于幂等去重 |
| `claims` | 否 | JSON **字符串**（不是对象），见下表 |

**❌ `settlement.json` 不能放 `$comment`**——字段集冻结，任何额外键都会被拒。说明写在你自己的 PR 描述里。

`claims` 的 7 个必需键（编码成一个 JSON 字符串）：

| 键 | 类型 |
| :--- | :--- |
| `schema_version` | integer |
| `score` / `volume` | integer（理论最高分 = 达成率分母） |
| `main_share` / `side_share` | number，和须为 1.0，主线 ≥ 0.5 |
| `main_failed` | boolean |
| `event_flags` | array\<string> |

**禁止键**：`grade` / `credits` / `payout` / `coefficient`——引擎自己从 `score`/`volume` 重算收益，副本不得直给。

> ⚠️ **CLI 通过 ≠ 设计合规**：`tools/validate.py` 只查结构（字段集、类型、公证、claims 结构与禁键、双报）。`shares` 加总、`main≥0.5`、轴取值范围等**设计规则 CLI 不查**——作者要自己守，审核会看。

---

## 本地自检（提交前必做）

```bash
python tools/validate.py content/instances/MY_STORY/settlement.json
```

退出码 0 = 结构合规。任何拒绝都是**单行**报告，含 `field` / `path` / `line` / `code` / `detail`，不会有堆栈。常见拒绝：

| 报告 | 原因 |
| :--- | :--- |
| `invalid_field:instance_id` + `is not a loaded instance` | 忘了先落 `instance.json`，或两处 ID 不一致 |
| `invalid_field:completion` | 写了 `completed` 而非 `success` |
| `invalid_field:$comment` | 把 `$comment` 放进了 settlement.json |
| `rejected_double_report:claims+credit_delta` | 带 claims 却写了非零 `credit_delta` |
| `rejected_unnotarized` | `ability_ids`/`item_ids` 未在词汇表公证，或 `enabled_in` 不含本副本 |

参考现成副本：[`D1`](D1/instance.json)（探索）、[`D2`](D2/instance.json)（契约场景标签 + 异构轴）。

---

## 红线（再强调）

1. 副本只交数据，不碰主神规则；账本只能由 `Engine.settle()` 写。
2. 不得发明未拍板的数值（税率、公证费、体量上限 —— 均为 `UNRATIFIED`）。
3. 剧情文本没有字段可放——把故事拆成 `axes` / `events` / `settlement_evidence` 声明。世界观描述写在 PR 里。
4. 同人世界观须显式标记社区内容池并遵守 takedown 规则，见 [`../../docs/TAKEDOWN.md`](../../docs/TAKEDOWN.md)。
