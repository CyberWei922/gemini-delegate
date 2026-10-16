# Gemini Delegate 安装与维护指南

这是给 Codex 或其他安装助手执行的完整流程。用户只需要说：

> 帮我按照这份指南安装：[https://github.com/CyberWei922/gemini-delegate/blob/main/AGENTS.md](https://github.com/CyberWei922/gemini-delegate/blob/main/AGENTS.md)。

收到仓库链接或本文件链接并明确要求安装时，先阅读本指南，再检查源码和执行步骤。
本指南使用标准文件名 `AGENTS.md`，位于仓库根目录；不另建 `agent.md`。

安装范围是本插件及必要依赖。遵守用户当次选择和宿主权限要求，保留已有工作、
其他插件、其他对话和账号设置；不读取或导出凭据，不把私人文件传给模型。
不要把“安装成功”“工具已加载”“模型可调用”混为一谈，最后需实际调用验证。

## 0. 从本指南开始执行

收到用户明确的安装请求后，完整阅读本文件，然后逐步完成第 1–5 节，
目标是安装插件并实际调用成功，而不只是给出计划或把命令交给用户。

- 源码仓库：[CyberWei922/gemini-delegate](https://github.com/CyberWei922/gemini-delegate)。
- 若 GitHub 页面未完整显示正文，读取[原始 Markdown](https://raw.githubusercontent.com/CyberWei922/gemini-delegate/main/AGENTS.md)。
- 第 1–2 节准备源码、依赖和账号；第 3 节安装；第 4–5 节确认工具加载并实际调用验收。
- 不执行用户已完成的重复安装，不擅自替换其他注册；首次 Google 登录由用户本人完成。
- 完成后说明安装位置、加载状态和实际任务结果。遇到无法继续的条件，指出具体卡点。

## 1. 准备源码与环境

把源码放在独立目录，避免放进用户正在开发的项目或覆盖已有改动：

```sh
git clone https://github.com/CyberWei922/gemini-delegate.git
cd gemini-delegate
```

已有相同源码目录时，先检查 Git 状态；不要重置、清理或覆盖未提交工作。
阅读 `README.md`、`scripts/install.py`、`scripts/doctor.py`、
`plugins/gemini-delegate/skills/delegate-simple-tasks/SKILL.md`。

环境要求：

- macOS、Linux 或 Windows 10/11，Python 3.9+、Git、Codex CLI、官方 Antigravity CLI（`agy`）。
- macOS 历史版本已实际调用验证，当前版本通过 macOS/Linux 回归；Windows 10/11 自 1.3.1 正式支持并已实际调用验证。安装者仍需核对自己的账号、网络和模型权限。
- 使用安装者自己的 Google 账号；会员身份本身不保证能访问指定 AGY 模型。
- 默认且固定模型为 `gemini-3.8-flash-high`。不共享作者账号、不降级模型、不改用付费 API。

若缺少 Python、Git 或 Codex，按用户的正常包管理方式或厂商官方说明补齐必要依赖。
若缺少 AGY，先查看 [官方 CLI 文档](https://antigravity.google/docs/cli/)，确认适合当前系统的安装方式。
不要使用不明来源的同名程序，也不要下载其他项目的 AGY 替代品。

Windows 使用 PowerShell，下面的 `python3` 命令改为 `py -3`；没有 Python launcher 时
使用已确认的 `python`。先阅读 [Windows 验收指南](docs/WINDOWS.md)。原生 `.exe` 和
npm Node `.cmd` 入口受支持；任意批处理包装不直接执行，需指定官方可执行文件。
不要混用 WSL 的 CLI 与 Windows Python。若官方 AGY 不提供适用入口，报告依赖卡点。

## 2. 检查依赖和账号

先执行只读检查，暂不进行模型推理：

```sh
python3 scripts/doctor.py
python3 scripts/install.py --dry-run
```

`doctor.py` 会检查 Python、平台、Codex、AGY 版本与必需调用参数（含 `--json-schema` 和 `--input-format`），以及指定模型的可用性。
它区分旧版 CLI、登录、网络错误、模型缺失和查询超时，并报告安全的退出码及检查阶段。
CLI 不在 PATH 中时，doctor 也支持 `--codex`、`--agy`；安装参数使用同样的路径。
`--dry-run` 只展示安装计划，不安装；模型列表可用也不等于实际推理成功。

需要登录时，让使用者打开官方 `agy`，本人完成 Google 登录。不要读取、复制、
打印或导出 OAuth 令牌。随后检查：

```sh
agy models
```

必须存在 `gemini-3.8-flash-high`。若账号、模型权限或环境仍不满足要求，报告具体原因，
不要隐藏失败、反复消耗已耗尽的额度或切换到 API 计费。

## 3. 检查已有注册并安装

先检查现有配置：

```sh
codex mcp get gemini_delegate --json
codex plugin list --json
```

没有该 MCP 注册是首次安装的正常情况。已有相同且健康的安装时可直接复用；
升级应符合用户的请求。若同名注册指向其他插件，先识别来源，不能静默覆盖。

然后执行：

```sh
python3 scripts/install.py
```

脚本会先检查 AGY 所需能力，再检测 Python 和 AGY 的真实路径，准备本机 marketplace，通过官方 Codex
命令安装 Skill 并注册 `gemini_delegate` MCP。它会私下备份 AGY 设置，只添加
本插件 `jobs` 目录的读取权限，并默认关闭额外付费 AI credits；其他字段保留。
每个步骤保存在私有安装回执中，失败时据此恢复，不删除原配置重新来过。

可选参数按实际需要使用：

| 参数 | 用途 |
| --- | --- |
| `--keep-credit-setting` | 用户明确要求保留额外付费 credits 偏好时使用 |
| `--replace-existing` | 核对旧注册且用户已授权替换时使用 |
| `--codex`、`--agy` | 指定不在 PATH 中的官方可执行文件 |
| `--agy-settings`、`--state-dir` | 指定已有设置文件或任务记录目录 |
| `--prepare-only` | 仅准备文件，用于隔离检查，不修改 Codex 或 AGY 注册 |

安装不修改全局 `AGENTS.md`、其他 MCP 注册或用户项目代码。

若只想浏览插件目录，可执行：

```sh
codex plugin marketplace add CyberWei922/gemini-delegate --ref main
```

添加 marketplace 不等于完整安装。首次使用仍需完成环境、权限、MCP 和实际调用检查。

## 4. 确认安装和工具加载

再次检查：

```sh
codex mcp get gemini_delegate --json
codex plugin list --json
```

确认插件启用，MCP 使用检测到的 Python、安装后的服务路径和预期环境。
检查当前会话是否暴露以下八个工具（1.4.0 包含 `usage_summary`）：

`gemini_status`、`delegate_task`、`get_task_result`、`cancel_task`、
`apply_task_changes`、`list_tasks`、`usage_summary`、`task_monitor`。

旧对话可能仍保留旧 MCP 进程或工具目录。可用宿主支持的方式只重新加载当前会话，
或先用新安装的兼容客户端检查同一个工作器。不要重启整个应用或中断其他对话。
客户端调用成功不能代替“当前原生 MCP 连接已刷新”的证明。

## 5. 实际调用 Gemini High 验收

调用前说明：“我会使用 Gemini Delegate 插件，让 Gemini High 做一次连接检查。”
通过 MCP 提交一个简短任务：只返回 `{ "check": "GEMINI_OK" }`，并用 JSON schema
要求这个准确值。传入真实项目的 `workspace`、中文标题 `Gemini 安装连接检查`、
默认 40 秒总期限，随后以每次最多 20 秒的等待读取异步结果。

验收要求：

- 状态是 `completed`，实际模型为 `gemini-3.8-flash-high`。
- 结果准确等于 `{ "check": "GEMINI_OK" }`。
- 报告真实任务 ID、尝试次数、失败或重试，以及 AGY 返回的用量。
- 用量缺失表示未知；空结果、权限拒绝、部分超时输出均不能算成功。

也可以运行仓库自带的真实 MCP 检查，会使用安装者自己的 Gemini 额度：

```sh
python3 scripts/smoke.py
```

可选验证双文件的一次性输入，沿用默认短时限：

```sh
python3 scripts/smoke.py --file-task --workspace .
```

当前会话没加载 MCP 工具时，使用安装目录中的
`plugin/scripts/delegate.py --input /path/to/temporary-task.json`。
参数 JSON 与 `delegate_task` 一致；客户端立即打印任务 ID，随后等待校验结果。
完成后删除临时任务参数文件，不把客户端成功误报为原生工具已加载。
兼容客户端与 `smoke.py --plugin-root` 自动读取所选安装包的运行环境。
显式 `--agy`、`--state-dir` 参数优先，其次为当前进程环境、安装配置和平台默认值。

认证、权限、网络或额度检查失败时，报告实际错误和仍未验证的部分，不宣称安装已全部完成。

## 6. 日常使用与分工

用户直接描述任务即可。适合 Gemini 的独立部分包括资料提取、文件清单、翻译、
数据整理和已经明确规则的机械修改。GPT 保留规划、架构、逻辑判断、根因分析和最终复核。

开始前说明使用 Gemini Delegate，并明确双方分工。尽早异步提交，主智能体继续
独立工作；依赖 Gemini 结果的步骤要等待并复核。交付时报告真实结果、任务 ID、
失败与重试，不把排队或失败当成成功。
文件快照由插件通过 stdin 一次性传入，不让模型逐轮读取清单和分块；任务仍应保持小而明确。
日常调用省略 `max_attempts` 使用默认 3 次启动恢复，不要习惯性设为 1；仅用户明确要求完全不重试时设 1。
读取 `progress` 区分启动、等待模型和处理；中间正文不回传，任何进度都不重置时限。

默认总执行预算 40 秒，单次调用上限 25 秒，不逐次延长；读取、AGY 槽等待、退避和全部尝试共用期限。
仅确认在启动阶段、15 秒内发生的临时连接失败自动重试，最多 3 次（首次加 2 次）。
一旦已有响应、用量或会话进展，或者不能确认尚未开始，就直接作废并交回主智能体。
空结果、格式错误、处理中超时和登录／权限／额度错误不重放。
`max_attempts` 可设 1–5；较大后台任务确有需要时显式调整 `timeout_seconds` 和
`attempt_timeout_seconds`，不要给简单任务自动增加到数分钟。详见[重试说明](docs/RETRIES.md)。
`retrying` 期间等待同一 ID；最终失败读取 `handoff`，再由主智能体接手。
JSON／修改任务使用 AGY 原生 Schema 格式约束，再做本地校验；未返回原生结构化结果时不接受普通文本替代。
数字和数组通过内部对象包装兼容，对调用者仍返回原本的 JSON 值。
成功结果立即返回；中文会话改名在独立后台元数据进程中处理，不占模型并发槽、不增加模型问答。
不要等待改名才使用模型结果，只有 `native_title.status: set` 才能报告改名成功。

按真实项目调用 `list_tasks` 查看记录。插件不会把 Gemini 注册成 Codex 原生
子智能体；不要用 GPT 桥梁或伪造记录模仿。网页看板仅在用户明确要求时打开。
分工可能提升整体速度，不保证每项任务提速，也不能用 Gemini tokens 直接换算 GPT 节省比例。

1.4.0 默认允许两个独立 Gemini 任务并发，可用环境变量或兼容客户端显式切回 1。
升级后实际验收，不要为了刷新连接中断其他对话。完整步骤见
[并发与用量说明](docs/CONCURRENCY.md)。每项任务传中文 `title` 和真实 `workspace`；
`usage_summary` 默认仅返回项目汇总，`include_tasks: true` 才附任务名和 AGY 会话编号。
合计包含有用量记录的失败尝试及重试，缺失记录标为未知；它不是完整账号账单。

1.4.0 在真实项目目录启动 AGY，由 AGY 原生保存和归属会话；首次运行会在
官方 `~/.gemini/config/agents/` 创建受限工作器定义，已有不同内容的同名配置保留并报错。
macOS/Linux 使用已就绪的官方交互界面执行 `/rename` 设置中文名，随后退出；
不能把 `/rename` 发给模型冒充成功。Windows 自动改名传输尚未适配，需如实报告。
检查 `native_title` 与原生会话记录，不把插件显示名当成原生改名证据。

## 7. 更新和卸载

更新前检查源码工作区和现有注册，保留本地改动及账号设置。获取用户所选的新版本后，
重新执行安装脚本和第 5 节的真实调用检查。若同名注册来自其他安装方式，先检查来源，
不要未经授权使用替换参数。

卸载前阅读 `scripts/uninstall.py`，先看计划再执行：

```sh
python3 scripts/uninstall.py --dry-run
python3 scripts/uninstall.py
```

只移除本安装拥有的 MCP、插件和 marketplace 注册，以及安装时新增的读取授权。
任务结果和备份保留；卸载不会重新启用额外付费 credits。
可选看板的停止方式见 [运行说明](plugins/gemini-delegate/README.md)。

## 8. 测试与贡献

提交修改前运行：

```sh
python3 -m unittest discover -s plugins/gemini-delegate/tests -v
python3 -m unittest discover -s tests -v
```

安装测试使用隔离临时目录和模拟 CLI，不改真实账号设置。
查看 [验证记录](docs/VERIFICATION.md) 了解实际测试范围；查看 [SECURITY.md](SECURITY.md)
了解问题报告方式；项目使用 [MIT 协议](LICENSE)。

每次插件发布以 `plugins/gemini-delegate/plugin.json` 为版本唯一来源，
同步兼容 manifest、README 徽章和 CHANGELOG。仅调整仓库文档无需改变运行时版本。
不要改历史标签或历史验收记录，不提交账号设置、凭据、任务输入或结果、备份、
生成的安装回执及厂商可执行文件。纯文档改动检查链接和渲染；涉及代码再运行相应测试。
