# Gemini Delegate

让 Codex 通过本机官方 Antigravity CLI（AGY），把独立的简单任务交给
**Gemini 3.8 Flash High**。GPT 负责复杂规划、逻辑判断和最终复核。

版本 **1.2.1** · MIT 开源 · 独立社区项目，由 CyberWei922 发起、AI 辅助开发。
本项目不隶属于 Google 或 OpenAI。

## 把链接交给 Codex 安装

复制下面这句话给 Codex：

> 帮我安装 https://github.com/CyberWei922/gemini-delegate 。先阅读仓库 AGENTS.md，按步骤检查依赖、安装插件，并实际调用 Gemini High 验证。使用我自己的 AGY 登录，不要改其他项目或改用付费 API。

[AGENTS.md](AGENTS.md) 包含逐步安装指导。Codex 能完成可自动化的步骤；首次
Google 登录需要你本人完成。安装成功和模型有权限，必须分别检查，最后还要
实际推理通过才算可用。

## 前提与手动安装

- macOS 或 Linux、Python 3.9+、Git、Codex CLI。
- 官方 `agy` 已安装并登录，`agy models` 包含 `gemini-3.8-flash-high`。
- 你自己的 Google 账号及模型额度。不会共享作者的会员或凭据。
- macOS 已实际调用验证；Linux 有自动测试，尚未做真实 AGY 调用验证。
  Windows 目前不支持。

```sh
git clone https://github.com/CyberWei922/gemini-delegate.git
cd gemini-delegate
python3 scripts/doctor.py
python3 scripts/install.py --dry-run
python3 scripts/install.py
```

然后在新的 Codex 会话里说：“使用 Gemini Delegate 做一次连接检查。”
当前会话没加载工具时，可用安装目录里的 `plugin/scripts/delegate.py` 验证同一
工作器。不要因此把 MCP 加载状态误报为成功。

安装脚本检测 Python/AGY 路径，不写死用户名或 Homebrew 位置。通过官方
`codex plugin marketplace add`、`codex plugin add` 和 `codex mcp add` 注册。
它会备份 AGY 设置，仅增加本插件 jobs 目录的读取权限，并默认关闭额外付费
AI credits；其他字段保留。`--keep-credit-setting` 可保留原偏好。
遇到已有不同 MCP 注册会停止，明确授权替换后才使用 `--replace-existing`。
安装不会改你的全局 AGENTS.md 或项目代码。

也可以先添加 GitHub marketplace 来浏览插件：

```sh
codex plugin marketplace add CyberWei922/gemini-delegate --ref main
```

仅添加 marketplace 不等于完成 Python/AGY 权限和 MCP 环境配置。
首次完整安装请按 AGENTS.md 或安装脚本执行。

## 日常分工与可见性

调用前会说明：

> 我会同时使用 Gemini Delegate 插件，让 Gemini High 整理资料；我继续制定方案。

插件异步返回任务 ID，Codex 在结果到来前处理独立工作。最终交付说明 Gemini
做了什么，并由 GPT 复核。需要依赖 Gemini 结果的步骤会等待；不会重复在 GPT
里做同一份处理。能否提速取决于分工和 AGY 启动、排队、复核成本。

| 适合 Gemini | GPT 保留 |
| --- | --- |
| 公开资料提取、文件清单、翻译改写、数据整理、明确的机械修改候选 | 规划、架构、逻辑判断、问题根因、风险判断、最终审查与应用修改 |

它是 MCP + Skill 插件，不会把 Gemini 注册成 Codex 原生子智能体，也不会
自动创建 GPT 桥梁或打开网页。调用记录、模型、状态和结果可通过 `list_tasks`
按项目查询；网页看板仅在明确请求时打开。

工具：`gemini_status`、`delegate_task`、`get_task_result`、`cancel_task`、
`apply_task_changes`、`list_tasks`、`task_monitor`。

## 执行与数据

- 固定 High 模型；官方 AGY 登录；不读取 OAuth、不调用私有端点、不回退 API。
- 单个 AGY 执行槽在聊天间共享；异步状态、取消、硬超时、至多一次有限重试。
- 拒绝空结果、权限拒绝、部分超时输出、无效 JSON 和不符合结果 schema 的输出。
- 只读明确提供的文件；修改先暂存，GPT 复核后应用，原文件哈希和候选哈希必须
  一致，保留备份。结果格式通过不代表内容或代码已正确。
- 网页读取仅支持公开 HTTP(S) 文本，不绕过登录或访问控制。
- 可选联网搜索依赖你已有的 `mcporter` Exa 配置；安装不会自动安装或登录它。
- 私有运行记录在 `~/.local/share/gemini-delegate/`，含任务标题、结果、来源、
  修改候选和备份；任务输入包执行后删除。Google/AGY 的保存策略独立适用。
  [数据说明](docs/PRIVACY.md) · [报告问题](SECURITY.md)

## 验证、更新与卸载

```sh
python3 -m unittest discover -s plugins/gemini-delegate/tests -v
python3 -m unittest discover -s tests -v
```

安装测试使用隔离的临时目录和模拟 Codex 注册接口，不改真实账号设置。
真实 AGY 验证范围见 [验证记录](docs/VERIFICATION.md)。测试支持不等于所有平台
都已做真实账号验收。

更新仓库后重跑安装脚本和实际连接检查。卸载：

```sh
python3 scripts/uninstall.py --dry-run
python3 scripts/uninstall.py
```

仅删除本安装拥有的注册和新增读取权限；任务结果及备份保留，也不会重新开启
额外付费 credits。可选看板进程关闭方法见 [运行说明](plugins/gemini-delegate/README.md)。

贡献请先读 AGENTS.md、运行测试并更新版本及 CHANGELOG。

可复制的日常指令：

- 用 Gemini Delegate 整理这些公开资料，你负责复核来源和结论。
- 这个任务由你规划，把能独立执行的简单部分交给 Gemini High 并行处理。
- 检查当前项目是否调用了 Gemini，给出真实任务记录和状态。
- 这次只用 GPT，不调用 Gemini。
