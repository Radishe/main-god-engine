# 开发环境备忘

记录本仓库在当前 Windows 环境下的已知约束，避免重复踩坑。

---

## 1. Git 相关

### 1.1 git.exe 位置

不在 `PATH` 中，需用绝对路径调用：

```
D:\tools\git\Git\cmd\git.exe
```

### 1.2 沙箱限制：**不要用管道捕获 git 输出**

本机处于文件沙箱下，`git.exe` 的输出被管道捕获时会失败：

```powershell
# ❌ 失败：Access is denied
$out = & $git --version | Out-String
$out = & $git status --short

# ✅ 可行：让输出直接继承到控制台
& $git --version
& $git status --short
```

如需在脚本里读取 git 输出，重定向到文件后读取文件，不要用管道。

### 1.3 仓库所有权检查（dubious ownership）

仓库目录属主是 `BUILTIN/Administrators`，但当前用户是 `Administrator`，
Git 会拒绝操作并要求设置 `safe.directory`。

**全局 `.gitconfig` 在沙箱外，无法写入**，因此用环境变量绕过：

```powershell
$env:GIT_CONFIG_COUNT    = "1"
$env:GIT_CONFIG_KEY_0    = "safe.directory"
$env:GIT_CONFIG_VALUE_0  = "D:/VirtualSharing/VirtualSharing/dsh/games"
```

> 若日后能写全局配置，更省事的做法是执行一次：
> `git config --global --add safe.directory D:/VirtualSharing/VirtualSharing/dsh/games`

### 1.4 提交者身份

同样因为全局配置不可写，提交时用环境变量提供身份：

```powershell
$env:GIT_AUTHOR_NAME     = "VoidRunner"
$env:GIT_AUTHOR_EMAIL    = "voidrunner@example.com"
$env:GIT_COMMITTER_NAME  = "VoidRunner"
$env:GIT_COMMITTER_EMAIL = "voidrunner@example.com"
```

### 1.5 一条可复用的调用模板

```powershell
$git = "D:\tools\git\Git\cmd\git.exe"
$g   = "D:\VirtualSharing\VirtualSharing\dsh\games"
$env:GIT_CONFIG_COUNT   = "1"
$env:GIT_CONFIG_KEY_0   = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = "D:/VirtualSharing/VirtualSharing/dsh/games"
$env:GIT_AUTHOR_NAME = "VoidRunner"; $env:GIT_AUTHOR_EMAIL = "voidrunner@example.com"
$env:GIT_COMMITTER_NAME = "VoidRunner"; $env:GIT_COMMITTER_EMAIL = "voidrunner@example.com"

& $git -C $g status --short --untracked-files=all
```

### 1.6 仓库本地配置说明

`.git/config` 中存在**重复的 `[core]` 段**——这是为了在无法写全局配置时，
把 `user` / `core` / `safe` 设置直接写进仓库本地配置。
Git 允许重复段且后者优先，**功能正常，不是损坏**。

---

## 2. Python 相关

`python` / `python3` 在 `PATH` 中指向 Windows Store 占位程序，**执行无输出**。
可用解释器：

```
D:\VirtualSharing\VirtualSharing\dsh\山西瀚晟同创环保科技有限公司标数项目\.survey_tmp\uvpythons\cpython-3.12.13-windows-x86_64-none\python.exe
```

---

## 3. 目录约定

| 路径 | 内容 |
| :--- | :--- |
| `docs/` | 设计文档（10 份），正式交付物 |
| `docs/_reports/` | 独立核验报告，质量审计痕迹 |
| `_evidence/` | 溯源证据，所有文档内容的事实来源 |
| `tools/` | 辅助脚本 |

---

## 4. 关于联网抓取

DeepSeek 分享链接的 API（`chat.deepseek.com/api/v0/share/content`）存在两个限制：

- **单次返回量不足以取回全部对话**，超出即被截断；
- **不接受分页参数**（`offset` / `limit` / `message_id` / `format` 均被忽略），
  始终从第 1 条消息返回，因此无法靠分页绕开截断。

**可行方案**：在浏览器中打开对话页 → `Ctrl+S` 另存为 HTML（渲染后的完整 DOM）
→ 用 `tools/extract_deepseek_html.py` 解析出全文。

> 该脚本按 `data-virtual-list-item-key` 切分轮次，并区分用户消息
> （`ds-collapsible-text`）与助手回答（`ds-assistant-message-main-content`）。
> 另存为 HTML 会同时产生一个同名 `_files/` 资源目录（JS/CSS/图标，体积大、
> 无内容），已在 `.gitignore` 中排除。