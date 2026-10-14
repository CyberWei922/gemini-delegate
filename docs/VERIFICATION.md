# Release verification: 1.3.0 (Windows preview)

Date: 2026-10-14. Windows-specific behavior is tested in the CI matrix with
Python 3.9/3.12; authenticated Windows AGY inference remains pending manual
verification using [WINDOWS.md](WINDOWS.md).

- Local macOS: 42 runtime tests (3 Windows-only skips) and 11 installer/protocol tests
  passed. Added cross-process file locking, non-destructive PID probing,
  argument preservation, legacy-console UTF-8 MCP round trips, parent-exit descendant cleanup, bounded streaming
  output, Windows Job assignment gating/failure and UTF-8 BOM settings coverage.
- CI includes Ubuntu Python 3.9/3.12, macOS Python 3.12 and Windows Python
  3.9/3.12. CI uses simulated CLI services and no login; final run results are recorded
  below once verified.
- A real 1.3.0 MCP server exposed all seven tools and invoked official AGY
  gemini-3.8-flash-high on macOS. Task d09e2a2c7f364fd3 returned GEMINI_OK
  in 11.73 seconds, one validated attempt, no retry, 3,398 reported tokens.
- Windows previews support native executable and standard npm Node batch
  entrypoints. Other batch wrappers fail without executing a shell. State lives
  under the current user's LOCALAPPDATA; NTFS access uses inherited ACLs.
- No native external-subagent registration, paid API fallback or automatic
  webpage was added. No real Windows/third-party-account login or membership
  inference is claimed.

## Historical verification: 1.2.2

Date: 2026-10-14. Verified on macOS with Python 3.14 and official AGY 1.3.4.

- 31 runtime tests and 9 installer/package tests passed locally. New regressions
  cover lossless UTF-8/CRLF/long-line snapshots, private input cleanup, budgets
  above 75 seconds, budget calculation after slot acquisition, bounded retries,
  a shortened budget after retry-slot contention and safe timeout diagnostics.
- A real new-package MCP server initialized as 1.2.2, exposed all seven tools and
  invoked authenticated gemini-3.8-flash-high to extract facts from 61,453 bytes
  of worker/test source. The result matched independently checked values in
  47.29 seconds, one attempt, with 54,360 reported tokens.
- The AGY execution transcript confirmed four view_file calls: a 1,697-byte
  manifest and all three raw text parts (24,490 / 16,620 / 20,343 bytes). Every
  view covered its full line range without byte truncation. All input parts and
  the manifest were removed after completion; original source stayed unchanged.
- The existing local plugin source was backed up, updated to 1.2.2 and reinstalled
  through the official Codex plugin command. Runtime files and installed cache
  were compared; the original MCP registration, membership account preference
  and unrelated registrations were preserved. The installed runtime suite passed.
- The newly installed compatibility client also completed an authenticated High
  JSON check in 11.87 seconds, one attempt, with 3,502 reported tokens.
- A running Codex chat can retain its old MCP process until that connection is
  reloaded. No app-wide restart or interruption of unrelated chats was performed.
  The updated compatibility client calls the same new AGY worker immediately;
  this must not be mistaken for verification that the old native connection has
  reloaded.

CI still covers Ubuntu Python 3.9/3.12 and macOS Python 3.12; inspect the actual
release commit's [Actions result](https://github.com/CyberWei922/gemini-delegate/actions).
These fixes do not add Windows support or native external-subagent UI support.
No authenticated Linux or third-party-account inference was tested.

## Historical verification: 1.2.1

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
