# Changelog

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
