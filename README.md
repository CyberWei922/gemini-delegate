<h1 align="center">Gemini Delegate</h1>

<p align="center">让 Gemini High 处理简单任务，让 GPT 专注规划、判断和复核。</p>

<p align="center">
  <a href="https://github.com/CyberWei922/gemini-delegate/releases"><img src="https://img.shields.io/badge/Version-1.7.0-007EC6?style=flat-square" alt="版本 1.7.0"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-007EC6?style=flat-square" alt="MIT 开源协议"></a>
  <a href="AGENTS.md"><img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square" alt="Python 3.9 及以上"></a>
  <a href="docs/VERIFICATION.md"><img src="https://img.shields.io/badge/macOS-CI%20passed-111827?style=flat-square" alt="macOS 回归测试通过，历史版本已实际调用验证"></a>
  <a href="https://github.com/CyberWei922/gemini-delegate/actions"><img src="https://img.shields.io/badge/Linux-CI%20passed-4c1?style=flat-square" alt="Linux 自动测试通过"></a>
  <a href="docs/WINDOWS.md"><img src="https://img.shields.io/badge/Windows-verified-007EC6?style=flat-square" alt="Windows 正式支持，已实际调用验证"></a>
</p>

<p align="center">
  <a href="AGENTS.md">安装指南</a> ·
  <a href="CHANGELOG.md">更新记录</a> ·
  <a href="docs/VERIFICATION.md">验证记录</a>
</p>

通过本机官方 Antigravity CLI（AGY），使用你自己的 Google 账号和模型额度。
独立社区项目，由 CyberWei922 发起、AI 辅助开发，不隶属于 Google 或 OpenAI。

1.7.0 一次性传入文件、报告真实流式进度，并使用 AGY 原生 JSON 格式约束与本地校验。
默认双任务并发，按项目汇总用量，并记录中文任务名称。
AGY 在当前项目中启动，并使用官方交互命令设置原生中文会话名（macOS 已实测；Windows 自动改名待适配）。
启动时的短暂连接失败最多尝试 3 次；处理中断直接作废并交回 GPT。默认单次 25 秒、总预算 40 秒，见[重试说明](docs/RETRIES.md)。
可显式切回单任务执行，使用方式与限制见[并发与用量说明](docs/CONCURRENCY.md)。

## 把链接交给 Codex 安装

复制这一句：

> 帮我按照这份指南安装：[https://github.com/CyberWei922/gemini-delegate/blob/main/AGENTS.md](https://github.com/CyberWei922/gemini-delegate/blob/main/AGENTS.md)。

完整步骤都在根目录 [AGENTS.md](AGENTS.md)：检查依赖、安装、登录、验证、更新和卸载。
链接直接打开安装指南，安装助手按其中步骤执行。首次 Google 登录由你本人完成。

## 前提与手动安装

- macOS、Linux 或 Windows 10/11，Python 3.9+、Git、Codex CLI，以及已登录的官方 AGY。
- `agy models` 中需要有 `gemini-3.8-flash-high`。
- macOS/Linux 跨平台回归通过；Windows 10/11 自 1.3.1 正式支持，已用官方 AGY 实际调用 Gemini High，见[验收指南](docs/WINDOWS.md)和[验证记录](docs/VERIFICATION.md)。

手动命令和缺少依赖时的处理，见 [安装指南](AGENTS.md#1-准备源码与环境)。

## 日常分工与可见性

| Gemini High | GPT |
| --- | --- |
| 资料提取、文件清单、翻译改写、数据整理、明确的机械修改 | 规划、架构、逻辑判断、根因分析、最终复核 |

调用前会说明使用 Gemini Delegate，随后并行处理独立工作，交付时报告实际结果。
你可以说：“把这个任务里简单的部分交给 Gemini High，你负责规划和复核。”

通过 `list_tasks` 查看真实任务记录。插件目前无法把 Gemini 显示为 Codex 原生子智能体；
网页看板只在你明确要求时打开。并行分工能否提速，取决于任务和调用开销。
`usage_summary` 按项目汇总所有记录和重试；统计分组不共享模型上下文。

## 执行与数据

- 固定 Gemini High，通过官方 AGY 调用会员额度，不切换到付费 API。
- 文件内容通过 stdin 一次性传入，支持流式进度、取消、硬超时和有限启动重试；修改须经复核后应用。
- 输入快照在任务结束后删除；结果和备份保存在本机。
- 公开网页读取可用；搜索需另有 Exa/mcporter 配置。

更多细节见 [运行说明](plugins/gemini-delegate/README.md) 和 [数据说明](docs/PRIVACY.md)。

## 验证、更新与卸载

命令与验收标准见 [安装指南](AGENTS.md#5-实际调用-gemini-high-验收)，测试范围见
[验证记录](docs/VERIFICATION.md)。问题反馈与贡献方式见 [指南末尾](AGENTS.md#8-测试与贡献)
及 [SECURITY.md](SECURITY.md)。

项目采用 [MIT 开源协议](LICENSE)。
