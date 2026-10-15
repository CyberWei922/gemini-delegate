# Windows 安装与验收

适用于 Windows 10/11、Python 3.9+。先验证本机依赖，再用你自己的 Google 账号验收。
自 1.3.1 起正式支持 Windows；真实 Gemini High 连接及中文分块读取已验证，详见
[验证记录](VERIFICATION.md)。自动测试使用模拟 CLI，不登录 Google；每位安装者仍需验证自己的账号和网络。

## 1. 准备环境

使用普通 PowerShell，安装 Python、Git、Codex CLI，以及当前系统适用的
[官方 Antigravity CLI](https://antigravity.google/docs/cli/)。登录由你本人完成。
本仓库不附带厂商程序，也不提供其他 AGY 替代程序。

```powershell
py -3 --version
git --version
Get-Command codex
Get-Command agy
codex --version
agy models
```

必须能看到 `gemini-3.8-flash-high`。如果没有 `py`，用已确认的 `python` 替换后续
`py -3`。不要混用 WSL 可执行文件和 Windows Python。原生 `.exe` 或 npm Node `.cmd`
入口可用；npm 入口还需要同一 Windows 环境中的 `node.exe`。任意自定义 `.bat/.cmd`
不会直接通过 shell 执行，需用安装参数指向官方原生或 npm 入口。

## 2. 获取并检查插件

放在独立目录；已有源码时先检查工作区，不覆盖未提交改动。

```powershell
git clone https://github.com/CyberWei922/gemini-delegate.git
Set-Location gemini-delegate
py -3 scripts/doctor.py
py -3 scripts/install.py --dry-run
py -3 -m unittest discover -s plugins/gemini-delegate/tests -v
py -3 -m unittest discover -s tests -v
```

`doctor` 应返回 `ready_for_install: true`。测试覆盖真实 Windows 文件锁、Job Object、
启动前归属校验、取消/超时及子进程清理、中文路径和 npm 参数传递；安装流程用临时
目录和模拟 CLI，保留真实账号配置。Node 不可用会跳过 npm 专项测试，其他失败应记录。

## 3. 安装与连接检查

按根目录 [AGENTS.md](../AGENTS.md) 检查同名注册。确认后执行：

```powershell
py -3 scripts/install.py
codex mcp get gemini_delegate --json
codex plugin list --json
py -3 scripts/smoke.py --workspace . --timeout 180
```

安装会保存私有设置备份，只添加插件 jobs 目录读取授权，并默认关闭额外付费 credits。
最后一条会消耗你自己的 Gemini 额度：应返回 `passed: true`、版本 `1.3.1`、模型
`gemini-3.8-flash-high`、真实任务 ID、尝试次数和 `GEMINI_OK`。不要把模型列表、排队、
超时、权限拒绝或空输出算作推理成功。

默认位置：

| 内容 | 默认路径 |
| --- | --- |
| 插件源码及安装回执 | `%USERPROFILE%\.codex\plugins\sources\gemini-delegate-community` |
| 任务结果、配置备份、共享锁 | `%LOCALAPPDATA%\GeminiDelegate` |
| AGY 设置 | `%USERPROFILE%\.gemini\antigravity-cli\settings.json` |

若官方 AGY 实际使用不同设置位置，使用 `--agy-settings` 指定；程序不探测或提取令牌。
`--agy`、`--codex` 可传完整路径，例如 `--agy "C:\实际安装目录\agy.exe"`。
doctor 支持相同的 CLI 路径参数，并检查版本、必需调用参数及模型查询错误。
备用客户端和 `smoke.py --plugin-root` 自动读取所选安装包的运行环境；也可用
`--agy`、`--state-dir` 显式覆盖，当前进程环境优先于安装配置。
自定义状态目录通过 `--state-dir` 指定；选择只有当前用户可访问的位置，Windows 使用
目录继承的 ACL，`chmod` 不等同于 NTFS 权限设置。

## 4. 验证文件读取与 Codex 调用

需要验证较大中文文件和权限时执行一次：

```powershell
py -3 scripts/smoke.py --file-task --workspace . --timeout 300
```

应该读取全部源文件分块并通过结构校验。若报 `permission_denied`，记录错误代码及拒绝
的动作，检查安装回执中的 jobs 读取授权是否写入 AGY 实际使用的设置文件。不要扩展为
全盘读取权限。输入快照在结束后删除，源文件不修改。

只打开一个新的 Codex 对话，或用宿主支持的方式刷新当前 MCP 连接；不要重启其他对话。
然后说“使用 Gemini Delegate，让 Gemini High 提取三个名称并去重，你复核结果”。
应看到插件调用记录、实际结果和任务 ID。兼容客户端成功与当前原生工具加载是两项
独立检查；插件不能注册为原生 Gemini 子智能体。

## 5. 故障与反馈

| 现象 | 检查方式 |
| --- | --- |
| 找不到 CLI／批处理入口不支持 | `Get-Command` 检查路径，使用原生 `.exe` 或标准 npm Node 入口 |
| 无法加入 Job Object | 保留 Windows 错误码；目标尚未启动，检查启动环境及系统策略 |
| model unavailable／认证失败 | 在官方 AGY 中本人登录，再检查 `agy models` |
| timeout／partial output | 失败不可用作结果；窄化任务或明确增加总预算，取消后检查无残留调用 |
| 中文乱码 | 使用 Python 客户端读取 UTF-8 结果；PowerShell 5 显示时用 `Get-Content -Encoding UTF8` |

反馈提供 Windows 版本、Python/Codex/AGY 版本、测试失败摘要、任务 ID、错误代码和
重试次数即可。不要发完整设置、OAuth 信息、私人任务输入或带 token 的看板链接。

需要卸载时，先阅读根指南，然后运行 `py -3 scripts/uninstall.py --dry-run` 查看计划。
确认属于本安装后运行 `py -3 scripts/uninstall.py`；任务结果和备份保留。
