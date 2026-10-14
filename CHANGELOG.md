# Changelog

## 未发布（文档）— 2026-10-14

- 简化 README 并保留主要章节，安装指令直接链接 AGENTS.md 安装指南。
- 居中展示标题与版本、MIT、Python、平台徽章。
- 将完整安装、验证、更新和卸载流程集中到中文 AGENTS.md。
- 补充安装助手从指南入口获取源码、逐步执行安装并实际验收的说明。
- 仅调整文档，运行时版本保持 1.2.2；检查 GitHub 渲染、链接和徽章。

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
