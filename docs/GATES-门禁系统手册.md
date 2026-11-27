# GATES · 门禁系统可复用手册

> 面向对象：想把这套「刚性测试 + 并行派活 + 不可伪造合入」机制用到别的项目的维护者。
> 本文描述的是**当前已实现的机制**（核对自 `gates/check.py`、`.github/workflows/gates.yml`、分片 json），不是设计愿景。
> 配套：`00-阶段与验收标准.md` §12（并行研发契约）、`设计决议记录.md`、`CONTRIBUTING.md`。

---

## 0. 这套系统解决什么问题

一句话：**先把「什么算做完了」写成机器可判定的测试，再放手让多个 agent 并行做，且不让任何 agent 改裁判规则来让自己通过。**

三个核心痛点与对应机制：

| 痛点 | 机制 |
| :--- | :--- |
| 「做完了」各说各话 | 每条验收 = 一个 `TEST <id> <PASS\|FAIL\|PENDING>` 测试文件；测试由 manifest 登记 |
| agent 并行会互相踩 | 分片（shard）声明 readonly/writable，hash 锁定，写路径零重叠检测 |
| agent 改测试刷绿 / 绕过门禁 | 分片归维护者所有 + 绿线棘轮（PASS 不得转红）+ CI 标签闸门 + CODEOWNERS review |

**关键的反直觉点**（复用时最容易搞错）：

1. **红阶段是合法的**。`GATE_EXIT: DENIED`、`FAIL`/`PENDING`/`MISSING` 不表示项目坏了——它们表示「开发还没做完」。真正的阻塞判据是 §4.1 的 `HANDOFF: READY`，不是全绿。
2. **绿线棘轮才是 CI 的合入判据**，不是「全绿」。见 §5.2。
3. **包级 PASS ≠ 集成 PASS**。包内用 `fake_settle`/`fake_notary` 替身自检，真实正确性由集成门 X04 终裁。见 §6.2。
4. **`judge_test` 不读断言内容**，只验协议（一行 TEST、id 对、状态与退出码一致）。所以「测试写了」不等于「测试有效」——见 §8.1。
5. **能转绿的红才是好红**。为了把数字弄好看而补空壳测试，是这套系统明令禁止的。见 §8.2。

---

## 1. 目录地图

```
gates/
├── manifest.json          判据本体：阶段 → gate → tests 的登记表（维护者所有）
├── baseline.json          绿线棘轮：每个测试上次的状态（维护者所有，CI 合入判据）
├── check.py               唯一裁判 CLI，6 个模式（见 §3）
├── coverage.json          契约覆盖：spec 条款 ↔ 代码 ↔ 包 的映射
├── evidence_rules.json    例外：哪些测试转绿必须附证据（目前只有 C30-01）
├── mutation_recipes.json  变异配方：X05 用它证明测试真能抓 bug
├── integration_job.json   集成门 X04 的装配顺序
├── package_hashes.json    7 个分片文件的 hash，检测篡改
├── packages/P1..P7.json   分片工单：每个 agent 的只读/可写边界、验收、依赖、DoD
├── stubs/                 契约替身与冻结契约（settlement/notary/loader/vocabulary…）
├── fixtures/              F1~F6 固定输入
└── tests/                 全部测试文件（<id 小写>.py）+ common.py 报告协议
```

**归属铁律**：`gates/`、`.github/`、`config/`（根）、`docs/设计决议记录.md`、`docs/00-阶段与验收标准.md` 是**裁判面**，由维护者所有；agent 只能写 `src/`、`content/`、`tests/<包>/`、`config/<包>/`、`evidence/`。这套边界由 `.github/CODEOWNERS` + CI 的 `protect-referee` job 双重保证。

---

## 2. 测试文件契约（最小可运行单元）

每个测试是一个独立 `.py`，文件名 = 测试 id 小写（如 `S0-G1-02` → `gates/tests/s0-g1-02.py`）。

**协议**（来自 `gates/tests/common.py`）：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, emit          # ROOT = 仓库根

ID = "S0-G1-02"

def main():
    # ... 真断言：读文件 / 跑子进程 / 调真实组件 ...
    return emit(ID, "FAIL", "具体原因")       # 失败
    return emit(ID, "PENDING", "缺前置条件")  # 设计性等待
    return emit(ID, "PASS", "证据摘要")       # 通过

if __name__ == "__main__":
    sys.exit(main())
```

**退出码**：`PASS=0`、`FAIL=1`、`PENDING=2`、`DEFERRED=3`。必须**恰好打印一行** `TEST <ID> <STATUS> <reason>`。

**裁判怎么判**（`check.py: judge_test`）：exit=0 + 恰好一行 TEST + id 匹配 + 状态与退出码一致，四条全中才算 PASS。这堵住了「伪造输出」和「最后一行覆盖」两个漏洞——但**它不读断言内容**（见 §8.1）。

**写真断言的三条经验**：

1. 优先用**真实组件**（`Engine.settle()`、validation CLI、`grade_for()`），别自造替身冒充。
2. 每条测试都要**做反证**：临时破坏被测对象（删字段、改配置、塞非法值），确认测试真的 FAIL，再恢复。没有反证的 PASS 可能是空壳。
3. 证据文件（如 `evidence/s3/g1-02.json`）由测试运行时**真实写出**，不要手写固定字符串充数。

---

## 3. CLI 六模式（`python gates/check.py <flag>`）

| 模式 | 作用 | 关键输出 | 是否阻断 CI |
| :--- | :--- | :--- | :--- |
| `--run` | 执行全部测试 | `runner: PASS=.. FAIL=.. PENDING=.. MISSING=..`、`GATE_EXIT` | 否（红阶段合法） |
| `--coverage` | 契约覆盖报告 | `spec_covered=`/`code_covered=`/`GAPS`/`HANDOFF` | 否（informational） |
| `--invariants` | I1~I8 全局不变量 | 逐条 `I<n> PASS/FAIL`、`INVARIANT_EXIT` | 否（informational） |
| `--baseline` | **绿线棘轮** | `regressions=`/`improved=`/`new_red=`/`BASELINE_EXIT` | **是** |
| `--write-baseline` | 固化当前状态为新基线 | `BASELINE written: … (N tests, PASS=M)` | 维护者手动 |
| `--package <P>` | 生成自包含工单 | `SHARD_INTEGRITY`/`STARTABLE`/`RUN_EXIT`（加 `--run` 才跑测试） | 否 |

**组合示例**（日常自检一次跑全）：

```bash
python gates/check.py --run          # 看全局红绿构成
python gates/check.py --baseline     # 确认没有绿转红（CI 同款）
python gates/check.py --coverage     # 确认 HANDOFF: READY（放手判据）
python gates/check.py --invariants   # 确认 8/8 ALLOWED
python gates/tests/x04-01.py         # 集成门终裁
python gates/tests/x05-01.py         # recipe 重放（碰 src/core 后必做）
```

---

## 4. manifest：判据本体

`gates/manifest.json` 是**唯一判据**，00 文档里的表格只是人类可读索引。结构：

```json
{
  "exit_rule": "pending_count == 0 and missing_active_files == 0 and runner_exit == 0",
  "layers": { "invariant": "…", "config_driven": "…", "human_in_loop": "…" },
  "stages": {
    "s0": [ {"gate": "G1", "layer": "invariant", "status": "active",
             "depends_on": [], "tests": ["S0-G1-01", "…"]} ],
    "s1": [ … ], "s2": [ … ], "s3": [ … ], "s4": [ … ],
    "sc": [ … ],   // shared contract suite
    "si": [ … ]    // cross-stage / integration
  }
}
```

### 4.1 三层 layer

- **`invariant`**：不依赖玩法数值，可直接写成测试。**必须 `active`**。
- **`config_driven`**：骨架先写、断言引用 config；配置定稿前**必须保持 `pending`**，`check.py:76-104` 会强制校验这条，改 active 会被拒。
- **`human_in_loop`**：机器留痕 + 人工动作（签字、PR、复现）。机器不能假装它自动化。

### 4.2 两态 status

- `active`：测试文件必须存在，否则计入 `MISSING`。
- `pending`：测试不必存在，但**必须声明 `depends_on`**。它表示「等前置条件」，不是「跳过」。
- 封存项的正确表达：保持 `pending` + 在 `note` 里写明「显式封存、不转绿」，而不是删条目或造假绿。

### 4.3 阶段视角 vs 分片视角

- **S0~S4** 是时间视角（进度）：第一阶段门禁、引擎、副本/公证、规则数值、治理。
- **P1~P7** 是分片视角（分工）：每个 agent 的可写边界。
- **能不能放手只由 `--coverage` 的 `HANDOFF: READY` 决定**，与 `GATE_EXIT` 无关。

---

## 5. 红绿语义与棘轮（最容易误解的部分）

### 5.1 为什么允许红

`--run` 的 `FAIL`/`PENDING`/`MISSING` 是**开发起点**：测试先写（红），实现随后跟上（转绿）。如果要求全绿才准开工，就等于禁止 TDD 和并行开发。§12.6 明确：`GATE_EXIT: DENIED` 是预期状态。

### 5.2 绿线棘轮是真正的合入闸门

`baseline.json` 记录每个测试上次的状态。`--baseline` 的判据（`check.py:227-285`）：

| 变化 | 判定 | 后果 |
| :--- | :--- | :--- |
| PASS → 非 PASS | `regressions` | **DENIED**（CI 拦） |
| 基线里的测试消失 | `missing` | **DENIED** |
| FAIL/PENDING → PASS 但无证据 | `unproven` | **DENIED**（见 `evidence_rules.json`） |
| FAIL/PENDING → PASS 且有证据 | `improved` | ALLOWED，提示 `--write-baseline` 固化 |
| 新测试且为红 | `new_red` | ALLOWED（只展示） |

**结论**：红可以存在、可以新增；**绿一旦达成就不能倒退**。这就是「棘轮」——单向收紧。

**维护者规矩**：测试转绿并验证后，跑 `--write-baseline` 把新绿线固化，否则下次 `--baseline` 会把这些提升当作 `improved` 反复提示。

---

## 6. 分片派活流程

### 6.1 工单生成

```bash
python gates/check.py --package P4           # 只看工单与阻塞判定
python gates/check.py --package P4 --run     # 加跑本包测试
```

输出的关键信号（两者独立）：

- **`SHARD_INTEGRITY: OK`**：分片未被篡改（hash 对得上 `package_hashes.json`）。TAMPERED 时拒绝发放工单。
- **`STARTABLE: YES/BLOCKED(...)`**：`blocked_by` 里的决议是否已 resolve——**阻塞判定**。
- **`RUN_EXIT: PASS/NOT_PASS(n)`**：本包 `tests` 是否全绿——**测试判定**。
- `shared_tests(PX final, informational)`：参与项由 PX 终裁，本包不判 PASS。

分片 json 的字段：`readonly`/`writable`（写边界）、`tests`/`shared_tests`（验收）、`global_invariants`（全局底线）、`runtime_depends_on`（运行时依赖）、`blocked_by`（等哪些决议）、`definition_of_done`（DoD）。`shard_owner: maintainer` + `agent_can_edit_shard: false` 必须保持——否则 agent 能改自己的验收清单。

### 6.2 包级假 vs 集成真

工单输出 `fake_mode=on (N 个契约替身)` 时，表示本包用 `gates/stubs/fake_*.py` 自检，**不依赖其他包的真实实现**。这让并行成为可能，但：

- 包级 `RUN_EXIT: PASS` **不等于**真实链路正确；
- 必须等所有包交付后跑 `X04-01`（`integration_job.json` 定义的装配顺序）做集成终裁；
- `X01`（交接）、`X02`（桩一致性）、`X05`（recipe 重放）共同构成跨阶段防线。

### 6.3 派活前先判「有没有活」

**别为派而派**。派活前跑一遍：

```bash
for p in P1 P2 P3 P4 P5 P6 P7; do python gates/check.py --package $p --run | grep -E 'STARTABLE|RUN_EXIT'; done
```

若全部 `STARTABLE: YES` + `RUN_EXIT: PASS`，说明「把 own 转绿」已无活可派。此时正确做法是**维护者亲自处理受保护路径上的剩余项**，而不是硬造一个工单——agent 写了也合不进去（CODEOWNERS 要求 owner review）。

---

## 7. CI 与合入治理

### 7.1 GitHub Actions（`.github/workflows/gates.yml`）

两个 job：

1. **`protect-referee`**（仅 PR）：检测受保护路径变更（`gates/`、`.github/`、`config/`、`docs/设计决议记录.md`）；若变更存在，PR 必须带 `gate-approved` 标签，否则 FAIL。
2. **`gates`**：
   - `--coverage`（informational，`continue-on-error`）
   - `tools/validate.py`（**阻断**）
   - `--baseline`（**阻断**，真正的合入判据）
   - `--invariants`（informational，`continue-on-error`）

### 7.2 CODEOWNERS

受保护路径全部 `@<owner>`：

```
/gates/          @owner
/.github/        @owner
/config/         @owner
/docs/设计决议记录.md   @owner
/docs/00-阶段与验收标准.md  @owner
```

**关键约束**：

- 免费私有仓库不强制 branch protection / CODEOWNERS review——需 Public 或 Team/Enterprise 账户。
- `gate-approved` 标签只能由 owner 贴，防止 agent 自批。
- **署名统一为 owner 会造成自审死结**：如果所有提交都是 owner 署名、又要求非本人 review，则 `human_in_loop` 类验收（如身份合规）结构上不可达。这类项要么引入第二 reviewer，要么显式豁免留痕——不要写假证据绕过。

### 7.3 标准合入流

```
agent 交付（只写可写路径）
  → 维护者跑全量 + baseline + invariants + X04/X05 + 零越界 diff
  → 提 PR（改了受保护路径就贴 gate-approved）
  → owner review + approve
  → CI 绿 → 合入
  → --write-baseline 固化新绿线
```

---

## 8. 反模式清单（复用者最容易踩的坑）

### 8.1 弱断言：「看起来真，其实抓不住」

`judge_test` 不验断言内容，所以以下都曾真实发生过：

- **只扫 ASCII 数字**：中文决议里塞「百分之十」照样 PASS → 必须同时扫中文 numeral。
- **引用解析形同虚设**：`_ref_resolves` 只要字符串含 `§` 就返回 True → 假引用 `§99.999` 照样过。必须校验标题存在 + 正文长度。
- **存在性检查当验收**：`if "字段" in doc` 就算过——空壳也能刷绿。

**防法**：每条测试做反证（§2）。宁可要 1 条能抓 bug 的强断言，不要 10 条摆设。

### 8.2 为刷绿造假

明令禁止：

- 往 `gates/tests/` 塞 `print("TEST X PASS")` 空壳；
- 把 `config/*.json` 的 `UNRATIFIED` 改成编造数值；
- 从 manifest 删条目冒充 MISSING 清零；
- 降低 baseline 绿线 / 改 recipe 锚点让 X05 过；
- 手写 evidence 文件充数。

**判据**：如果一条红项的「转绿」需要发明素材里没有的东西，正确动作是**显式封存**（pending + note 写明不转绿），不是硬转。

### 8.3 契约与产物错配

规格写了 D1/D2 提交 CLI，但 D1 实际是副本声明、D2 是 human_in_loop 产物——都没有结算清单字段。此时：

- 不要在测试里伪造一个「D1 清单」；
- 用真实存在的合法产物（如 F4 fixture）测可达契约，在 docstring 里**如实记录 mismatch**；
- 同步修订 00 契约表（否则 review 时会认为测试错了）。

### 8.4 把 informational 当判据

`--coverage`、`--invariants` 在 CI 里是 `continue-on-error: true`。它们红了**不会**拦 PR——只有 `--baseline` 会。别看到 CI 全绿就以为这两个信号也正常，要单独看它们的输出。

### 8.5 格式噪音污染判据文件

用脚本改 `manifest.json` 时，`json.dumps(indent=2)` 会把原本紧凑的条目全展开（曾造成 300 行纯格式 diff）。**用精确字符串替换改判据文件**，保持 diff 最小、review 可读。

---

## 9. 从零复用：最小落地清单

给一个全新项目套这套机制，按顺序做：

1. **定判据本体**：写 `manifest.json`（layer/status/depends_on/tests），00 文档写人类可读验收表。
2. **建报告协议**：`gates/tests/common.py`（`emit` + 退出码）+ 一个示例测试。
3. **建基线**：先让核心测试绿，跑 `--write-baseline` 生成 `baseline.json`。
4. **建契约覆盖**：`coverage.json` 把 spec 条款映射到包与代码；跑 `--coverage` 直到 `HANDOFF: READY`。
5. **建分片**：按可写路径不重叠拆 P1..Pn，每个写 `packages/Pn.json`，生成 `package_hashes.json`。
6. **建不变量**：I1~In 写成全局检查（字段冻结、无硬编码字面量、无越界 import…）。
7. **建集成门**：`integration_job.json` 定义装配顺序，X01~X05 做交接/桩/回归/集成/变异防线。
8. **建 CI 治理**：CODEOWNERS + `protect-referee` job（受保护路径 + 标签闸门）+ `--baseline` 阻断。
9. **开跑**：先判 `HANDOFF: READY` 再派 agent；日常盯 `--baseline` 零回归；碰裁判面前先想清楚谁 review。

---

## 10. 本项目的当前状态快照（示例）

> 仅作「这套机制跑起来长什么样」的参照；活数据以命令输出为准。

```
全量      PASS=62 FAIL=3 PENDING=3 MISSING=4  GATE_EXIT: DENIED（预期红阶段）
coverage  HANDOFF: READY         ← 已达放手判据
baseline  ALLOWED, regressions=0 ← CI 合入闸门正常
invariants 8/8 ALLOWED
X04 8/8 / X05 5/5 recipe 重放
决议 D14~D24 全闭环，无待拍板项
```

剩余红项全部有正当理由：D14 已废弃的机制、D23 显式封存的时间轴/自审项、需真人动作的 human_in_loop、无对应内容不可编造的项。**没有一条是「能安全转绿」的**——这是机制健康的表现，不是缺陷。
