# 审核标准（REVIEW）

> 贡献契约四件套之一，小节标题登记于 `config/docs.json`。审核口径只引用已拍板契约；未拍板参数只登记缺口，不在此写死数值。

## 分层治理权限

沿用 08 §1 的 L0~L3（原文标题为「三层权限」，表内实为四层）：

| 层级 | 角色 | 权限 |
| :--- | :--- | :--- |
| L0 | 框架维护者 | 定底层规则、阶位区间、结算公式骨架、惩罚原则；调汇率；批准晋升试炼；修改物品/能力基准值；设定家族风格标签 |
| L1 | 副本审核者 | 按固定 checklist 审批副本提交、公证物品/能力注册、家族变体 |
| L2 | 副本作者 | 写副本内容、声明属性轴、提交注册申请 |
| L3 | 玩家 | 进副本、游玩、兑换 |

L0 对受保护路径的改动仍需 CODEOWNERS 审核与 `gate-approved` 标签，不因层级而豁免（见下文）。

## 审核 checklist

08 §2 的 11 项已逐项闭环，结构化结论在 `config/checklist.json`：

- 每项 `status` 只允许 `defined` / `removed`。
- `status=defined` 的项带被检查对象定义，是有效检查项：`2`（属性轴取值范围）、`7`（建议基准值）、`8`（绑定类型与稀有度）、`9`（家族风格标签）、`11`（主神接口直接调用 / 引擎内部导入）。
- `status=removed` 的项不再检查：`1`（版本号）、`3`（`can_modify_persistent_state`）、`4`（结算模板 ID）、`5`（基准分/最低比值）、`6`（阶位推导）、`10`（最低差异要求）。移除原因逐项登记在配置中，勿按旧文档补回。
- 判定规则：有效项全部通过才放行；任一项不通过退回并附原因。

## 机检与人工判断

- **机检**：`tools/validate.py` 做 Schema 校验；C01-01 扫描声明式清单中的引擎逻辑令牌；C12-01 用 `gates/stubs/forbidden_imports.json` 拒绝引擎内部导入；I4 锁定结算字段集哈希。机器门失败即 PR 检查不通过。
- **人工**：L1 只做二元判断，不需要理解副本玩法——例如第 9 项只判断变体设定是否匹配家族风格标签，不审剧情衔接；第 7 项核对建议基准值落在品质参考区间。
- 通道差异：声明式 JSON 走机检；DLL 高级通道按 D15 走 `separate_review` 与 `restricted_sandbox`，不得用机检绿结果代替独立审核。

## CODEOWNERS 与 gate-approved 标签

- `.github/CODEOWNERS` 是审核权来源：`gates/`、`.github/`、`config/`、`docs/设计决议记录.md`、`docs/00-阶段与验收标准.md` 归 `@Radishe`。
- 受保护路径变更须由该 owner 审核，并携带 `gate-approved` 标签；CI 的 `protect-referee` 作业会检测路径并要求标签，`CODEOWNERS` 不得留 `REPLACE_WITH_MAINTAINER_TEAM` 占位符。
- 禁止自批：被审 agent 不得修改裁判面、不得自行打标签。绿线收紧（`--write-baseline`）与分片变更（`--write-package-hashes`）同样属于维护者审批范围。
- 完整流程留痕顺序：`submitted` → `ci_validated` → `human_reviewed` → `merged`，各恰好一次。

## 社区内容池与同人副本

- 副本以原创或公共领域 / 授权明确的世界观为主；同人性质副本须显式标记为社区内容池内容，并保留 takedown 通道（08 §6）。
- 版权与移除契约见 [TAKEDOWN.md](TAKEDOWN.md)。
- 未拍板参数：L1 审核人数门槛、L0 维护者人数、审核者选拔机制、申诉通道与时限（08 §5）均未定；本文只登记缺口，不写具体人数或时限。
