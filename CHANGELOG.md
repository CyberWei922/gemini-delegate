# Changelog

## 1.7.0 — 2026-10-16

- 文件、网页和上下文通过单次 stdin 提示一次性传入，去掉模型读取清单／文件分块的往返；保留 UTF-8 原文、显式文件范围和独立上下文。
- 使用官方 stream-json 报告初始化、等待模型、模型／工具步骤和终态；仅保存有界进度元数据，中间正文不回传主智能体。
- 默认保留最多 3 次启动恢复，修正 Skill 中容易被误用的 max_attempts=1；仅明确的快速启动连接失败可重试，处理中断或阶段不明直接作废。
- 保持单次 25 秒、总执行预算 40 秒；进度不续期。失败时保留已报告的部分用量并标为不完整，终态用量不与步骤用量重复累计。
- 包含此前本地 1.6.1 原生 JSON 约束；源码、实测和平台验证范围见 docs/VERIFICATION.md。

## 1.6.1 — 2026-10-15（本地试用）

- JSON 和文件修改任务接入官方 AGY `--json-schema`；原生结构化输出通过本地校验后才接受，不退回普通文本冒充成功。
- Schema 使用私有临时文件，执行结束后删除；仅记录格式模式、摘要哈希和是否收到原生结果。
- 安装预检检查原生 Schema 能力；保留单次 25 秒／总预算 40 秒和处理中断不重试规则。
- 实际测试与兼容性范围见 docs/VERIFICATION.md。

## 1.6.0 — 2026-10-15

- 简单任务默认单次 25 秒、总执行预算 40 秒，取消逐次延长的超时预算。
- 仅在 15 秒内确认发生于启动阶段的临时连接失败自动重试，默认最多 3 次；处理中断或无法确认阶段直接作废并交回主智能体。
- 空结果、格式校验失败、登录／权限／额度错误不重放；保留真实失败证据和已报告／未知用量，部分结果不应用。
- 成功结果先返回，官方中文会话改名移至有期限的后台元数据助手，不占模型执行槽、不增加模型问答。
- 验证范围与实际调用记录见 docs/VERIFICATION.md。

## 1.5.0 — 2026-10-15

- 默认最多 3 次 Gemini 尝试，超时、空结果、格式错误与已识别临时网络故障自动重试，再交回主智能体。
- 总预算改为 300 秒，默认调用预算约 60／90／120 秒；可设总次数 1–5、首次上限与总期限，超时重试必须有更长可用预算。
- 重试退避释放并发槽且可取消；中间失败的原生改名跳过，避免消耗模型重试时间。
- 失败结果提供明确 handoff；Skill 在重试中等待同一任务，防止 GPT 提前接手或重复提交；登录、权限和额度问题直接报告。
- 保留每次尝试和用量，未知用量不记为零。验证包含真实进程故障注入及随后官方 Gemini High 恢复，详见 docs/VERIFICATION.md。

## 1.4.1 — 2026-10-15

- 发布此前确认保留的双任务并发、原生项目归属、中文会话名和项目 Token 汇总；各模型任务上下文独立。
- 合并远端 1.3.1 的 Windows 任务可见性、AGY 预检及安装配置读取修复，不覆盖已发布的历史。
- 并发参数同样遵循显式参数、进程环境、安装配置、默认值的优先级，兼容自定义 AGY 和任务目录。
- 更正工具标题说明，区分任务名称和官方 AGY 原生改名的实际状态；Windows 自动原生改名仍未适配。
- 识别首次进入项目时的官方信任提示，立即报告需要使用者确认，避免把权限等待误报为改名超时；不自动批准整个项目的权限。
- 验证：macOS 92 项运行时测试（4 项 Windows 专项跳过）、14 项安装／协议测试通过；实际调用和远端 CI 见 docs/VERIFICATION.md。

## 1.4.0 — 2026-10-15

- 使用者确认保留原生项目归属、中文会话名、项目用量汇总和独立上下文，升级现用安装。
- Gemini 默认并发从 1 改为 2，仍可显式选择串行；安装配置与兼容客户端采用同一默认值。
- 增加旧 MCP 版本检查指引：连接未刷新时直接使用已升级的兼容客户端，不中断其他对话。
- 自动验证：66 个运行时测试（macOS 跳过 4 个 Windows 专项）、11 个安装／协议测试通过。
- 从实际安装位置验证新版默认设置与真实调用；具体任务、用量和原生记录保存在本机升级回执。
- Windows 自动原生改名仍未适配；本次本机升级不包含公开发布或新远端 CI。

## 1.4.0-preview.2 — 2026-10-15（本地试验，未发布）

- 官方 AGY 改为在 Codex 的真实项目目录启动，由其原生机制保存和归属会话；输入快照继续私有隔离。
- 使用官方全局 agents 路径发现受限工作器，保留已有同名定义并检测两种目录形式的冲突。
- macOS/Linux 在官方交互界面就绪后执行 `/rename`，设置原生中文会话名并退出；
  改名受并发名额、取消和总期限约束，不发送新的模型问答，不直接写原生会话存储。
- 明确处理 AGY 1.3.5 print 模式不支持改名及启动提示绕过命令分发的问题；Windows 自动改名尚未适配。
- macOS 两项 Gemini High 任务并发通过，各一次成功，无模型重试；调用重叠约 16.35 秒，
  合计报告 11,911 tokens。原生记录核对：两个不同会话、工作区均为 Briskill、中文名准确、各 2 个模型步骤。
- 自动验证：66 个运行时测试（4 个 Windows 专项跳过）、11 个安装／协议测试；未执行新远端 CI 或 Windows 真实账号验收。

## 1.4.0-preview.1 — 2026-10-15（本地试验，未发布）

- 可选两个 AGY 调用并发，跨新版进程共享两个槽；默认仍为单任务，试验使用独立状态目录。
- 新增按完整项目路径汇总的 usage_summary，覆盖全部记录和重试；缺失用量显式保留未知。
- 中文工作名称写入提示词和记录，关联 AGY 真实返回的会话编号；每次调用保持独立上下文。
- 提供兼容客户端统计／JSON 导出和隔离的真实并发验收脚本；等待使用者核对 Token Monitor 后决定保留。
- 验证：macOS 56 个运行时测试（4 个 Windows 专项跳过）和 11 个安装／协议测试通过；
  两个 Gemini High 任务一次成功、无重试，进程重叠约 17.06 秒，报告总用量 9,948 tokens。
  本轮未执行 Windows 真实账号验收或远端 CI。

## 1.3.1 — 2026-10-14

- Windows 10/11 转为正式支持；实际 Gemini High 连接及中文分块读取验证通过，macOS/Linux/Windows 五组 CI 全部通过。
- 修复 Windows 进度快照临时不可读时任务列表漏项：读取使用有限重试，本进程任务以内存记录补全，继续按项目过滤并保留隐私处理。
- doctor 报告 AGY 版本、必需参数、模型查询退出码和超时，并区分升级、登录、网络故障与模型不可用；支持自定义 CLI 路径。
- 安装在修改文件、账号设置或注册前检查 AGY 所需能力，拒绝不兼容的旧版 CLI；隔离准备和 dry-run 保持无注册行为。
- 兼容客户端与真实 MCP 验收脚本读取已安装包的运行环境；优先级为显式参数、当前进程环境、安装配置、平台默认值。
- 新增 `--agy`、`--state-dir` 客户端覆盖参数及跨平台回归；macOS/Linux 默认目录、AGY 模型和 POSIX 进程清理行为保留。
- 验证范围：68 项运行时测试、14 项安装/协议测试，Windows 额外 60 次本进程及 20 次跨进程任务可见性回归；任务 ID、用量、重试和验证范围见 docs/VERIFICATION.md。

## 1.3.0 — 2026-10-14

- 简化 README 并保留主要章节，安装指令直接链接 AGENTS.md 安装指南。
- 居中展示标题与版本、MIT、Python、平台徽章。
- 将完整安装、验证、更新和卸载流程集中到中文 AGENTS.md。
- 补充安装助手从指南入口获取源码、逐步执行安装并实际验收的说明。
- Windows 10/11 预览适配：字节文件锁、Job Object 与启动门控、进程树取消/超时清理、LOCALAPPDATA 状态目录。
- 对 Windows 短暂文件共享冲突增加有上限的原子替换重试，保留旧任务记录直至替换成功。
- 原生和 npm Node CLI 入口通过参数数组调用，未知批处理拒绝执行；中文路径、UTF-8 协议和 BOM JSON 兼容。
- 跨平台流式输出有硬上限；超时保留安全字节统计，清理可重复调用；系统异常保留 errno/winerror 便于排查。
- 修正 Windows 粗粒度计时下的浮点预算边界，并额外重复 20 轮任务记录并发回归。
- Windows Python 3.9/3.12 CI 和 PowerShell 手动验收指南；真实 Windows AGY 登录与会员推理仍待手测。
- 验证范围：44 个运行时测试（macOS 跳过 4 个 Windows 专项）、11 个安装与协议测试；CI 和实际调用见 docs/VERIFICATION.md。

## 1.2.2 — 2026-10-14

- Replaced escaped one-line input bundles with a bounded manifest and lossless
  UTF-8 text snapshots up to 24 KiB each; preserve real line breaks and page
  truncated tool views. Remove all input snapshots after execution.
- Removed the hidden 75-second attempt cap. By default AGY uses the remaining
  overall budget, calculated after acquiring the shared slot. Added an explicit
  optional first-attempt cap with deadline-bounded timeout retries only when a
  longer next attempt is possible, rechecked after slot waiting.
- Added validation-specific retry feedback, per-attempt timing and safe partial
  output-size diagnostics without retaining source/output fragments in metadata.
- Verification: 31 runtime and 9 installer/package tests; actual Gemini High
  file-task verification is recorded in docs/VERIFICATION.md.

## 1.2.1 — 2026-10-14

- Removed unnecessary reverse DNS from the loopback monitor bind and increased
  its startup deadline to 20 seconds; added DNS-independent binding and startup
  failure diagnostics tests.
- Verification: both automated suites rerun locally and in the GitHub CI matrix;
  AGY worker behavior is unchanged from the live-tested 1.2.0 release.

## 1.2.0 — 2026-10-14

- Prepared the MIT-licensed public repository and portable marketplace package.
- Added step-by-step AGENTS.md for URL-driven Codex installation and actual
  authenticated Gemini smoke verification, plus a read-only prerequisite doctor.
- Added managed/idempotent installation and scoped uninstallation, dynamic
  Python/AGY paths, private settings backups and conflict detection.
- Added explicit runtime path overrides and isolated installer tests.
- Kept High-only AGY execution, asynchronous plugin cooperation and reviewed
  edits. Native Gemini subagent UI registration is not an implemented feature.
- Verification scope and platform limitations are recorded in docs/VERIFICATION.md.

The local development history is retained in the plugin's CHANGELOG.md. Private
task records and machine-specific verification files are not distributed.
