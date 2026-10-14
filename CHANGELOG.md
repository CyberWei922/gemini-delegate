# Changelog

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
