# Gemini Delegate runtime

See the repository [README](../../README.md) and [AGENTS installation guide](../../AGENTS.md).
The canonical version is in `plugin.json`; the Python server reads it at startup.
This directory is the portable plugin bundle, including its MIT license.

Eight tools expose status, asynchronous submission/result/cancellation, reviewed
file application, project task history, usage_summary and an optional read-only task monitor.
The Skill teaches Codex to announce Gemini Delegate, dispatch independent work
early and continue its own planning/review concurrently. These are agent
instructions, not a forced routing hook or native Gemini subagent registration.

Runtime requirements: macOS/Linux or Windows 10/11, Python 3.9+, authenticated official AGY and
the exact `gemini-3.8-flash-high` model. No third-party Python dependencies.
The worker fixes this High model and invokes AGY with bounded print mode, JSON
streaming output, sandbox hints and an isolated worker agent. AGY defaults to two
independent concurrent calls; explicit concurrency 1 selects serial execution. Calls are stopped as a process tree on cancellation/hard timeout (POSIX
process groups; Windows Job Objects with a gated launcher). A
confirmed startup connection failure within 15 seconds can retry, up to three total
attempts by default. Mid-task interruptions, unconfirmed phases, empty/invalid output
and account/permission/quota failures stop without replaying generated work.
Partial results are discarded and terminal failures expose handoff to the primary agent.
The wrapper rejects soft-denied, empty or partial-timeout success envelopes and
validates structured results. JSON/edit tasks pass a private schema file to the official
`--json-schema` option and require native `structured_output`; ordinary text is unchanged.
Schemas are removed after execution. Native output still undergoes local schema and
edit-scope validation; missing native payload is a failure, without text fallback.

The default total execution budget is 40 seconds and each call is capped at 25 seconds.
There is no escalating timeout. Retrieval, shared-slot waiting, backoff and all attempts
share one deadline starting when a queued worker begins execution. Fixed caps are
rechecked after slot waiting; cancellation/process cleanup can add a short grace period.
`attempt_timeout_seconds` (`--attempt-timeout`) overrides the fixed call cap;
`max_attempts` (`--max-attempts`) accepts 1–5 total attempts. Only explicitly bounded
background work should request longer budgets. Do not auto-resubmit a terminal failure.
Handoff is an MCP result/instruction, not an automatically spawned GPT agent.
Failed-attempt titles are skipped; native IDs and reported usage remain for accounting.
See [retry behavior and examples](../../docs/RETRIES.md).

Optional environment overrides: `GEMINI_DELEGATE_AGY` and
`GEMINI_DELEGATE_STATE_DIR`; `GEMINI_DELEGATE_MAX_CONCURRENCY` defaults to 2
(only 1 or 2 accepted). The installer records the detected paths in its
local MCP registration. Runtime defaults use the current user's home and PATH.
The compatibility client and repository smoke client read the selected plugin's
installed runtime paths. Precedence is explicit `--agy`/`--state-dir` options,
process environment, installed manifest, then platform defaults. Only this
plugin's two runtime path variables are loaded; account settings are not read.
Windows state defaults to `%LOCALAPPDATA%\GeminiDelegate`. Native `.exe` and npm
Node `.cmd` entrypoints are supported without passing task arguments through a
shell. Unknown batch wrappers fail with an actionable error. UTF-8 is explicit
for protocol/files; the compatibility client accepts PowerShell UTF-8 BOM JSON.
See the [Windows manual check](../../docs/WINDOWS.md) and the version-specific
[verification record](../../docs/VERIFICATION.md). Windows support is stable
from 1.3.1; each user's account/model/network access still needs its own check.

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
python3 scripts/delegate.py --usage --workspace /absolute/project
python3 scripts/delegate.py --usage --workspace /absolute/project --export project-usage.json
python3 scripts/delegate.py --workspace /absolute/project --title "整理名称" \
  --instruction "提取唯一名称，保持顺序" --context "Alice, Bob, Alice"
```

The optional monitor is opened only when explicitly requested, with
`task_monitor` or `scripts/delegate.py --monitor`. It listens on loopback and
requires a private random token; no browser is automatically opened. To stop
its persistent process, read the PID from the private runtime `dashboard.json`,
verify it belongs to `server/dashboard.py`, then terminate that specific process.
Do not publish the monitor URL. No arbitrary filesystem endpoint is provided.

Input files are snapshotted in memory and delivered together in one bounded UTF-8
prompt through stdin, without shell interpolation, command-line bodies, manifest
reads or model file-read rounds. The official --input-format/--output-format
stream-json protocol is used for one fresh turn per task; stdin closes after that
single input. No history is reused. Private JSON schema files are removed after
execution. Results/backups and bounded progress metadata stay private on disk.

Progress distinguishes startup, awaiting_model and processing; only official
agent/tool steps count as processing. It reports event/step counts and times,
not intermediate text, thought content, source bodies or tool parameters.
No progress resets/extends the 25-second call cap or 40-second total default.
A terminal result is required; a disconnected partial stream is discarded.
Reported step usage from interrupted calls is partial, counted once and explicitly
incomplete; terminal usage replaces the step subtotal for completed calls.
Leave max_attempts unset (default 3) to retain startup recovery; use 1 only when
no retries were explicitly requested. Init/input echoes alone cannot make a
silent hard timeout eligible for replay. Google/AGY retention is independent.
Uninstall deliberately retains work.

`usage_summary` reads all recorded tasks, including records beyond the 200-row
task-list limit, and counts retries once. Compact totals are the default;
`include_tasks: true` / CLI `--include-tasks` adds readable names and native
conversation ID mappings when AGY reports them. CLI exports include these details
and refuse to overwrite existing files. Thinking/cache fields are reported
separately and never added again to total_tokens. Every model attempt uses a
fresh one-turn AGY stream-json call in the real project directory, without history continuation.
Input snapshots are private in-memory values passed once through stdin. The restricted worker
is discovered through official `~/.gemini/config/agents/`; conflicting user
definitions are preserved and reported.

On macOS/Linux, the official TUI is resumed only to type `/rename` after its
editor is ready, then `/exit`. This changes the native title without a model
turn. Never send `/rename` via print mode or `--prompt-interactive` in AGY 1.3.5.
Successful model results return before naming completes. A separate bounded metadata
helper uses its own lock and never holds model execution slots. Read native_title
status again before claiming the name was set; pending is not success. Windows native title transport
is explicitly unsupported pending ConPTY implementation; project cwd still works.
Uninstallation currently retains the global worker definition; remove it only
after confirming it is unchanged and unused. Native conversations remain owned
and stored by AGY. Token Monitor display is independently checked by the user.
Use a fresh state directory for concurrency trials alongside older workers;
see [trial instructions](../../docs/CONCURRENCY.md).
