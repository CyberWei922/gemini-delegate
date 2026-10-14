# Gemini Delegate runtime

See the repository [README](../../README.md) and [AGENTS installation guide](../../AGENTS.md).
The canonical version is in `plugin.json`; the Python server reads it at startup.
This directory is the portable plugin bundle, including its MIT license.

Seven tools expose status, asynchronous submission/result/cancellation, reviewed
file application, project task history and an optional read-only task monitor.
The Skill teaches Codex to announce Gemini Delegate, dispatch independent work
early and continue its own planning/review concurrently. These are agent
instructions, not a forced routing hook or native Gemini subagent registration.

Runtime requirements: macOS/Linux or Windows 10/11 (preview), Python 3.9+, authenticated official AGY and
the exact `gemini-3.8-flash-high` model. No third-party Python dependencies.
The worker fixes this High model and invokes AGY with bounded print mode, JSON
output, sandbox hints and an isolated worker agent. An AGY process is serialized
across chats and stopped as a process tree on cancellation/hard timeout (POSIX
process groups; Windows Job Objects with a gated launcher). A
recoverable output failure may retry once. A timeout retry requires an explicitly
bounded first attempt and a strictly longer available retry budget. The wrapper rejects soft-denied, empty or
partial-timeout success envelopes and validates structured results.

The default 180-second overall execution budget includes retrieval, shared-slot
waiting and all attempts after the worker starts. Each call uses the remaining
budget; there is no hidden 75-second cap. `attempt_timeout_seconds` (CLI:
`--attempt-timeout`) optionally caps the first call; a retry can use up to twice
that cap, bounded by the remaining total budget and rechecked after slot waiting.
Cancellation/process cleanup may take a short additional grace period.

Optional environment overrides: `GEMINI_DELEGATE_AGY` and
`GEMINI_DELEGATE_STATE_DIR`. The installer records the detected values in its
local MCP registration. Runtime defaults use the current user's home and PATH.
Windows state defaults to `%LOCALAPPDATA%\GeminiDelegate`. Native `.exe` and npm
Node `.cmd` entrypoints are supported without passing task arguments through a
shell. Unknown batch wrappers fail with an actionable error. UTF-8 is explicit
for protocol/files; the compatibility client accepts PowerShell UTF-8 BOM JSON.
See the [Windows manual check](../../docs/WINDOWS.md); real Windows account
inference remains unverified until that check is completed.

Public webpages are fetched through a bounded read-only adapter, excluding
private/credential URLs and non-text content. DNS proxy handling verifies public
addresses independently and requires certificate-verified HTTPS. Optional search
uses an existing Exa/mcporter backend, not one installed by this bundle.

Only explicitly supplied UTF-8 files up to 128 KiB are read, within the given
workspace. Original content is excluded from live progress records. Inputs are
read through a small manifest and raw UTF-8 parts of at most 24 KiB, preserving
line endings and multibyte characters. Long context, search and webpage text use
the same snapshots; all parts and the manifest are deleted after execution. Edits are
returned as candidates; application requires review, unchanged original/artifact
hashes, backups and conflict checks. JSON schema success is not semantic proof.

The CLI compatibility client runs the same worker:

```sh
python3 scripts/delegate.py --list --workspace /absolute/project
python3 scripts/delegate.py --workspace /absolute/project --title "整理名称" \
  --instruction "提取唯一名称，保持顺序" --context "Alice, Bob, Alice"
```

The optional monitor is opened only when explicitly requested, with
`task_monitor` or `scripts/delegate.py --monitor`. It listens on loopback and
requires a private random token; no browser is automatically opened. To stop
its persistent process, read the PID from the private runtime `dashboard.json`,
verify it belongs to `server/dashboard.py`, then terminate that specific process.
Do not publish the monitor URL. No arbitrary filesystem endpoint is provided.

Input bundles are deleted after each execution. Task metadata/results, evidence
hashes, candidates and backups remain private on disk. Google/AGY retention is
independent. Missing usage means unknown. Uninstall deliberately retains work.
