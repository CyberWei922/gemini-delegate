# Release verification: 1.2.1

Date: 2026-10-14. Verification used macOS, Python 3.14 and Codex CLI 0.162.1.

- 20 runtime tests: strict output/schema handling, cancellation/deadline process
  cleanup, public URL checks, staged edits/conflicts/backups, private previews,
  live records/recovery, monitor access and runtime environment paths.
- 9 installer/package tests using temporary homes and a simulated Codex CLI:
  full install/uninstall, idempotency, foreign registration protection, explicit
  replacement, partial failure recovery, invalid settings, dry-run and Unicode
  paths. Real user HOME/CODEX_HOME were not changed.
- A real prepared package initialized over MCP from a path containing spaces
  and Chinese characters. No real Codex registration was changed by this check.
- The native Codex app-server parsed the public marketplace/package read-only.
- A real public-package MCP server exposed all seven tools and invoked the
  official authenticated AGY CLI with gemini-3.8-flash-high. The JSON smoke check
  returned GEMINI_OK in 15.13 seconds, one attempt, with 3,431 reported tokens.
- A separate optional documentation task failed at Google's eligibility check
  with a connection reset. That task was not reported as generated content;
  the main agent wrote the documentation.

GitHub CI runs the same two automated test suites on Ubuntu (Python 3.9/3.12)
and macOS (Python 3.12). Inspect the actual [Actions results](https://github.com/CyberWei922/gemini-delegate/actions)
for the release commit; CI is not an authenticated Gemini test.

Not tested: a fresh third-party Google account, real AGY inference on Linux,
Windows, or native Gemini subagent activity-list integration. No browser
substitute or GPT bridge was added. Full registration tests use a simulated CLI
to avoid changing existing user registrations; real staged MCP startup and AGY
inference were tested separately.

The real AGY smoke result above was obtained from 1.2.0. Release 1.2.1 only
changes optional monitor binding/startup and test diagnostics; its AGY inference
worker is unchanged. The first CI run found the five-second monitor startup
limit insufficient on macOS; the corrected release is checked in CI again.
