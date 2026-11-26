# 贡献指南（CONTRIBUTING）

> 贡献契约四件套之一，小节标题登记于 `config/docs.json`。本文件只复述**已拍板**决议：D15（JSON 一等公民）、D17（Python 原型工具链）、D18/D20/D21（评分链）、CODEOWNERS 与 `gate-approved` 标签保护。未拍板事项只登记缺口，不在此补写规则。

## 贡献通道

D15 定稿：**声明式 JSON 副本是一等公民**，覆盖绝大多数场景，可机检、可走 Schema validation CI；**带自有逻辑的 DLL 是显式标记的高级通道**，仅用于确需自定义逻辑的场景。

- 默认通道：声明式 JSON。清单只声明数据，不含 `settle()` / 账本写入 / 惩罚逻辑；静态扫描命中即拒绝（契约来源 `gates/stubs/settlement.json`、`config/contribution.json`）。
- 高级通道：DLL 需满足 `config/contribution.json` 登记的三项条件——`explicit_flag`、`separate_review`、`restricted_sandbox`。D15 细化 D9 而非推翻：能力保留，但不再是默认路径。
- 边界：声明式清单禁止导入引擎内部命名空间，唯一令牌来源为 `gates/stubs/forbidden_imports.json`，命中以 `rejected_import` 拒绝加载。

## 提交前自检

1. 运行 config/paths.json 登记的校验入口 `tools/validate.py`；CI 中该作业是 blocking，失败即 PR 检查不通过（S4-G1-03）。
2. 自查审核 checklist：现行有效项见 `config/checklist.json` 中 `status=defined` 的条目；`status=removed` 的条目不是检查项，勿按旧文档补写字段。
3. 不要提交未拍板的数值：场景标签逐标签规则（C15）、扭曲节点结算单元边界（C16）仍为 UNRATIFIED；评分数值以 D20/D21 与 `config/scoring.json`、`config/tiers.json` 为准，不在 PR 里另造一套。
4. 变更 `config/` 下的共享契约或评分数值属于受保护路径，见「审核与合入」。

## 审核与合入

流程标记按 S4-G4-02 登记的顺序留痕：`submitted` → `ci_validated` → `human_reviewed` → `merged`，各恰好一次，CI 阶段退出码为 0。

- 机器门：`gates/check.py --baseline` 是 blocking——绿线只能收紧，任何曾为 PASS 的测试转红即拒绝合入。
- 人工门：受保护路径（`.github/`、`gates/`、`config/`、`docs/设计决议记录.md`、`docs/00-阶段与验收标准.md`）须由 `@Radishe` 审核，并携带 `gate-approved` 标签；`gates.yml` 的 `protect-referee` 作业会检测这些路径并要求标签。
- 禁止自批：被审 agent 不得自行添加 `gate-approved`，也不得修改裁判面使其判定通过。`CODEOWNERS` 是唯一审核权来源。
- 审核 checklist 的执行口径见 [REVIEW.md](REVIEW.md)。

## AI 辅助生成内容责任

贡献者对其提交中的 AI 辅助生成内容负责：提交即表示已确认内容不侵犯第三方权利、不含未授权的可分发素材，并已按 [TAKEDOWN.md](TAKEDOWN.md) 知悉移除通道。AI 生成内容的著作权与供应链风险按 01 §6、08 §6 的已登记结论处理，不因工具自动化而转移责任给维护者。

## 训练数据供应链

若贡献流程调用了第三方模型或资产服务，训练数据的合规性会沿供应链传导到最终游戏（01 §6 / 08 §6）。贡献者须在提交中披露所用外部模型 / 资产服务及其已知授权状态；无法确认授权状态的素材不要提交。项目方不替第三方训练数据的合规性背书。

## 项目方保留移除权

对侵犯第三方权利、授权状态不明或违反本契约的内容，项目方保留移除的权利，通道见 [TAKEDOWN.md](TAKEDOWN.md)。此权利不因内容已合入或已打上 `gate-approved` 标签而失效。
