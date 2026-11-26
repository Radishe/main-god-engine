# Schema 契约（SCHEMA）

> 贡献契约四件套之一，小节标题登记于 `config/docs.json`。本文件只描述已拍板的结构契约；字段集以 `gates/stubs/settlement.json` 与 `config/` 下共享配置为准，不在本文另立数值。

## 声明式副本清单

D15 定稿：声明式 JSON 是一等公民。清单是**数据声明**，不是可执行逻辑：

- 不得含 `settle()`、账本写入、惩罚逻辑等引擎语义；静态扫描令牌见 `gates/stubs/settlement.json` 的约定与 C01-01。
- 不得导入引擎内部命名空间；唯一令牌来源 `gates/stubs/forbidden_imports.json`，命中即 `rejected_import`。
- 属性轴按 01 §2 的概念声明取值范围；场景标签字段名为 `scene_tag`，见下文「场景规则标签」。
- 带自有逻辑的 DLL 不是清单的一部分，走 `config/contribution.json` 的独立高级通道。

## 结算清单与冻结字段

`gates/stubs/settlement.json`（version 2）是结算清单字段集的唯一结构来源：

- `settlement_manifest.required`：实例 ID、轮回者 ID、完成态、`credit_delta`、能力 ID 列表、物品 ID 列表。
- `optional`：`idempotency_key`、`claims`。
- `frozen: true`，并带 `field_set_digest`。不变量 I4 禁止任何包扩展字段集；扩展须同步更新哈希并经维护者独立审批。

D18 硬约束 1：`claims` 与**非零** `credit_delta` 双字段共存即拒绝（`rejected_double_report`），防止双报刷币。冻结字段集保留 `credit_delta` 是结构兼容需要，不代表它仍是权威 payout 来源。

## claims 结构化证据

D18 把 `settle()` 从加法器升级为规则引擎：副本通过版本化 `claims` 申报结构化证据，引擎独立重算评分与定级。

- `claims` 以 JSON 字符串编码；必需键：`schema_version`、`score`、`volume`、`main_share`、`side_share`、`main_failed`、`event_flags`。
- 裸 `score` / `grade` / `credits` 不作为支付值：禁止键见 `gates/stubs/settlement.json` 的 `claims_schema.forbidden_bare_keys`；`score`/`volume` 只是供重算的证据。
- 引擎只认中性键，不得读具体属性轴字面量（I2 扫描）；`engine_must_not_read` 登记了禁止读取的轴名。
- D20 定稿的链条：份额加总 100%、体量 = 理论最高分 = 达成率分母；达成率区间 S/A/B/C/D/E 与系数、汇率 1:1 以 `config/scoring.json` 为准；E 系数为 0.1，F 为独立失败态走 D14 简化惩罚，不接失败/抹杀计数。
- D21 定稿：阶位系数 `2^(n-1)`、区间下限 `1000×2^(n-1)`，副本阶位与玩家阶位共用同一把尺；以 `config/tiers.json` 为准。

## 场景规则标签

C15 已拍板的结构部分（见 `config/scenes.json` 的 `ratified`）：

- 标签枚举：`peaceful` / `raid` / `contract`。
- `affects_settlement: true`；清单字段名为 `scene_tag`；未知标签拒绝；由副本作者申报。

逐标签的具体公证 / 税率规则仍为 **UNRATIFIED**（`config/scenes.json` 的 `unratified.per_tag_rules`）。本文与 Schema 都不得塞入任何具体税率数值——那属于未拍板规则，须由拍板后另行定稿。

## 字段扩展与版本锁定

- 字段集由 `field_set_digest` 锁定；任何 required/optional 的增删都要重算哈希，并走 `@Radishe` 独立审批与 `gate-approved` 标签（D18 约束 3 / I4）。
- 评分数值的定稿状态见 `config/scoring.json` / `config/tiers.json`；未定稿期间相关 Gate 保持 PENDING，不得以占位值假装已就位（D18 约束 4）。
- 贡献通道的边界配置（`json_primary_dll_optin`）见 `config/contribution.json`，与本文共同构成 Schema 的可机检部分。
