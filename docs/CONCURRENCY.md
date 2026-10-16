# 原生项目会话、双任务并发与项目用量（1.7.0）

1.7.0 默认并发为 2，两项任务仍使用独立上下文，并保留 1.3.1 的 Windows 运行时修复。
真实账号的双任务验证不能证明所有网络、任务类型和平台均稳定；遇到具体问题可显式选择并发 1。
发布包、源码和验证范围见 GitHub Releases 及[验证记录](VERIFICATION.md)。

## 实际验收

在仓库根运行下面的脚本。它会使用运行者自己的官方 AGY 会员额度，发出两项独立任务，
仅快速且确认的启动连接失败允许有限重试，处理中断和校验失败不重放。`--state-dir` 必须是空目录，`--output` 必须尚不存在。
Python、AGY 和指定 High 模型需提前可用；不修改登录设置、安装注册或现用任务目录。
首次执行会在官方全局 agents 目录创建受限工作器定义，保留已有同名配置并报告冲突。

```sh
python3 scripts/concurrency_smoke.py --workspace /absolute/project \
  --state-dir /absolute/new-trial-runtime --output /absolute/new-trial-report.json
```

Windows 使用 PowerShell 的 `py -3`，把参数写在同一行。
新的并发逻辑尚未在 Windows 真实会员账号验收。
Windows 仍可按真实项目目录启动任务；自动中文改名需要交互终端传输，当前明确返回
`native_title.status: unsupported`，尚未实现 Windows ConPTY 路径，不宣称改名成功。

验收同时检查两项结果和各自的随机标记，记录两个进程的起止时间，检查调用重叠；
AGY 返回会话编号时保存真实编号并检查不同任务没有复用。进程重叠不等于能测量
Google 服务内部的推理调度，也不保证每项任务提速。

## 并发设置与上下文

- 只支持并发 1 或 2，默认 2。环境变量 `GEMINI_DELEGATE_MAX_CONCURRENCY=1` 或兼容客户端
  `--max-concurrency 1` 可显式选择单任务；普通调用无需额外传并发参数。
- 两个文件锁槽在同一状态目录的多个新版进程间共享，第三个调用等待；取消、超时和
  退出会释放持有的槽。新版串行工作器会保留两个槽，维持独占执行。
- 旧版工作器不认识第二个槽。新旧版混跑必须使用不同状态目录，待确认后再正常升级。
- AGY 在真实 `workspace` 中启动，按官方机制保存和归属会话；输入快照在内存隔离，通过 stdin 一次性传入。
  每次模型尝试启动新的 AGY 单轮 stream-json 进程，不传 `--continue` 或 `--conversation`。
  项目统计分组和任务标题不会把上一任务的内容写入下一任务。

## 项目汇总与中文名称

每次传入真实项目的绝对 `workspace` 和简短中文 `title`，例如「整理模型清单」。
记录会显示「项目名称 · 中文工作名」。标题也会放到 AGY 的实际提示词开头。
macOS/Linux 在模型结果校验后，通过官方交互界面的 `/rename` 设置同一条原生会话标题，
等待真正编辑器就绪后输入命令，再用 `/exit` 退出。成功结果先返回，改名后台处理；
后台元数据助手使用独立锁和 30 秒期限，不占两个模型调用槽，也不增加模型问答。
初始 `pending` 状态表示改名尚未完成，后续查询会合并实际结果。
不会直接写原生数据库，也不会把模型自称「已经改名」当成成功。

AGY 1.3.5 的 print 模式没有会话管理器，无法 `/rename`；`--prompt-interactive /rename ...`
会将文字作为模型输入，不能用于改名。后台改名只续接本项任务的 ID 执行元数据命令，
不会将此会话的历史传给另一项模型任务。`native_title.status: set` 代表收到官方界面确认；
失败、超时、无编号或平台不支持时明确记录状态，不重复执行已完成的模型任务。
Token Monitor 如何显示和刷新仍由使用者检查。
首次在某个项目打开官方交互界面时，AGY 可能要求信任该项目；插件返回
`native_title.status: requires_trust`，不会替使用者批准整个目录的读写和执行权限。
需要原生中文名时，由使用者在该目录运行 `agy`，阅读并选择是否信任。
已有模型结果仍有效；不要为了改名重复已成功的模型推理。
AGY JSON 响应中的会话／会话连接编号仅在真实返回时保存，用来建立名称对照。

MCP `usage_summary` 默认按项目返回简短合计；提供 `workspace` 可限定项目，
`include_tasks: true` 会附中文任务名和真实 AGY 编号。旧对话可能尚未加载新工具，
可用安装目录中的新版兼容客户端读取；客户端成功不代表旧原生 MCP 已刷新。

```sh
python3 plugins/gemini-delegate/scripts/delegate.py --usage --workspace /absolute/project
python3 plugins/gemini-delegate/scripts/delegate.py --usage --all-projects
python3 plugins/gemini-delegate/scripts/delegate.py --usage --workspace /absolute/project --export project-usage.json
```

读取试验目录时，给进程设置 `GEMINI_DELEGATE_STATE_DIR=/absolute/new-trial-runtime`。
输出 JSON 是本机报告，不需要网页，也不会自动打开浏览器。导出包含名称和会话对照，
拒绝覆盖现有文件；它不包含任务输入、模型正文或账号凭据。

统计按完整项目路径分组，同名但路径不同的项目不会合并。所有任务记录参与汇总，
不受 `list_tasks` 200 条展示上限影响；有记录的失败调用和重试用量也计入一次。
缺失或不完整的尝试计数单独展示，`usage_complete: false` 表示合计不完整。
思考和缓存计数保留 AGY 原值，不再次加到 `total_tokens`，以免重复。
这些是插件内的已报告用量，不能代替整个账号的完整账单。

## 更新和回退

升级前保留现用安装及注册的备份，再按官方安装流程更新并实际调用验收。
已经加载旧 MCP 的对话可能仍运行旧代码：先检查 gemini_status 的版本，旧连接未刷新时
使用安装后的新版兼容客户端，不中断其他对话。客户端成功不代表原生连接已经刷新。
回退只恢复对应插件文件和其注册，不删除其他工作、试验报告或任务记录；不要重置整个 Codex 配置。
若撤回首次创建的全局工作器定义，只能在内容仍与本插件定义一致且确认未被复用时移除，
不得删除用户自定义配置。AGY 自行保存的真实对话保留。
