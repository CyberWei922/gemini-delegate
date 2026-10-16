# Release verification 1.7.1

Date: 2026-10-16. Incident `8fb7cd8c60f947f0` used 1.7.0 and failed before inference
at 17.53s. Positive preflight evidence was recorded, but the separate 15s retry
cutoff wrongly disabled recovery. 1.7.1 removes this elapsed-time cutoff while
keeping the original total deadline, fixed call cap, independent contexts and
no replay for processing/unknown failures.

The transport also no longer waits for process-pipe EOF after a complete terminal
message. Lingering real subprocess tests cover completed success, terminal error
and a success envelope carrying a partial-output warning; only validated complete
results can be accepted. Progress now includes terminal SUCCESS/ERROR.

Initialization is now gated: no task bytes are sent until official init arrives.
If init is still absent at 10s, the process is stopped and can retry with positive
proof that the model never received the task. The 10s startup gate consumes the
same 25s call / 40s total budgets. Actual no-input AGY 1.4.0 readiness was observed
at 6.29s on macOS; this is not a model turn or shared task history.

## Verification scope

- 146 runtime tests passed on macOS (4 Windows-only skips), 14 installer tests.
  New coverage includes 17.53s confirmed startup recovery, insufficient remaining
  budget, slow generation failure without replay, safe failure diagnostics and
  terminal cleanup without waiting for a lingering process; success before task
  submission is rejected.
- Real official Gemini High extractions from three keyboard-related source files:
  `5bd41fc06f2b486d` 22.48s, `d53b8b6a98474be9` 21.59s and
  `56acf3407bc6467a` 19.22s. Each completed once and the full ordered function-name
  list matched local source extraction. The latter two used the final terminal
  cleanup path and recorded terminal SUCCESS.
- Larger 19,956-byte three-file request `1594def42d0d4565` failed at 27.89s;
  no partial output was used. Single-file extraction before the terminal cleanup
  fix, `9a0ce0c4fd554858`, also timed out and was not counted as success.
- Controlled 17.53s local preflight injection `93fdccb7687d4eb6` correctly retried
  the real High call, then exhausted its original 40s budget. It proves the retry
  branch, not successful recovery. Its first failure was simulated, not Google.

- Plain-text file extraction `d68fa0540079410d` completed once in 18.41s and
  exactly matched the source. Simple copied facts need not use native JSON.
- Before gating, the plain-text delayed-startup trial `278b2e9903564ee5` also
  exhausted the original budget and was not counted as success.
- Final gated recovery `80cd682356ea42b6`: the controlled local 17.53s startup
  stall was stopped at 10.01s with task_input_sent=false. The second attempt
  was real official Gemini High; task_input_sent=true, terminal SUCCESS, exact
  source function list matched, 28.54s total. Limits stayed 25s/40s, two attempts.
  The injected stall was not an actual Google failure. No GPT agent did the work.

These are bounded evidence, not a guarantee of provider latency. The calling
instructions now keep source-fact collection narrow, split independent files,
and retain regression planning in the primary agent. No task deadline increased.

---

## Historical verification — 1.7.0

# Release verification 1.7.0

Date: 2026-10-16. File/context/source bodies are sent in one bounded stdin prompt,
using official single-turn AGY stream-json. Model and task history stay independent.
The 25-second call/40-second total defaults and startup-only retry window are unchanged.

## Automated verification

- 136 runtime tests passed on macOS (4 Windows-only skips), and 14 installer/
  protocol tests passed. Public Skill frontmatter validation passed.
- New coverage: split UTF-8 stream events, stdout/stderr limits, large pipe input
  without deadlock, phase classification, cross-process live metadata, no leaked
  intermediate text, duplicate/malformed/truncated terminal events, partial usage
  accounting and deduplication, default startup retry after init, and no replay
  after agent progress. A real subprocess emits continuous progress until the
  original fixed deadline: it is stopped and partial work is discarded.
- Windows keeps its job-assignment launch gate and forwards the remaining stdin
  to the target without buffered pre-reading. Binary/Unicode pipe round-trip and
  rejection without a valid gate are covered by real subprocess tests.
- CLI capability checks now require --input-format as well as native --json-schema.
  The locally tested 1.6.1 native-JSON changes are included in this public version.

## Actual official Gemini 3.8 Flash High checks

- `dfadc163cafd4258`: Chinese deduplication/native JSON completed once in 16.53s,
  7,176 reported tokens; official init, agent/finish and terminal events captured.
- `111d500871ec440a`: two real input files, exact names/versions extracted once
  in 15.16s, 8,165 reported tokens. All source contents were sent in stdin, with
  zero required model file-read calls; five official stream events were observed.
- `938c0a37ed2d426d`: the public MCP `smoke.py --file-task` flow completed once
  in 15.47s, 8,282 reported tokens; both manifest entries matched, native JSON
  and terminal events validated, and observed `file_read_steps` was zero.
- `b0e40b7e145f403a`: two controlled local preflight EOF result events (not Google
  failures or model calls), then one real High response. Exact STARTUP_RECOVERED
  matched on attempt 3, total 16.03s, 7,120 reported tokens. Call caps stayed 25s;
  backoff was 0.25/0.5s. Missing injected-attempt usage remains unknown.
- `b6e5ff312d43436e`: larger three-script inventory still timed out after 28.05s
  including cleanup, one attempt, no retry, no result applied. Stream init and
  user-input receipt were observed; no model/tool execution event or terminal
  result arrived before the deadline. Stage remained unconfirmed, not a proven
  preflight failure. This failure is not counted as successful delegation.

These checks prove the new transport, native JSON, phase evidence and startup
recovery work; they do not prove all file tasks finish under 25s or a stable speedup.
Google/AGY can spend a quiet interval waiting/reasoning without output events.
Progress never renews the deadline; partial text never substitutes for success.

## Installation and platform scope

- Current-task versioned runtime was installed separately; existing shared Codex
  and OpenCode 1.6.1 files/connections remain unchanged while other chats run, per
  the user's instruction. No other chat was messaged, interrupted or restarted.
- Shared installation update is deferred until other work finishes. Installed
  files and native stdio connection versions must be checked separately; a new
  compatibility client does not establish native hot reload.
- Cross-platform CI must be checked on the actual published commit. No Windows
  membership live test or Windows native-title transport support is asserted.
- Machine-specific reports, task inputs, backups and credentials are excluded
  from the public repository. Historical verification follows below.

---

## Historical verification — local 1.6.1 trial


Date: 2026-10-15. JSON/edit tasks pass a private schema file to official AGY
--json-schema and require structured_output, followed by local schema and edit
validation. Ordinary text mode stays unchanged. Native schemas are deleted after
execution; metadata retains only format/hash/wrapper evidence.

AGY requires the schema root to be an object. Non-object or unspecified schemas
use an internal single-value object; callers still receive the original JSON
value. Native payload presence does not bypass local checks or source hashes.

## Actual Gemini 3.8 Flash High calls on macOS

- Prompt-only 1.6.0 baseline `65c72243edec44bf`: hard timeout after 29.02 seconds
  including cleanup, one attempt, no retry, no reported usage. Partial work was
  discarded. The task's model cap was 25 seconds and process cap 27 seconds.
- Native-schema object task `ab8e353c76ad44f6`: completed once in 18.32 seconds,
  no retry, 7,230 reported tokens. Exact name deduplication/count matched; both
  native_json_schema and structured_output_reported were true.
- Initial unconstrained-schema compatibility task `23c931e1f3104b32`: rejected
  by CLI before inference (0.20 seconds, no retry, usage unknown). A separate
  CLI diagnostic confirmed that schema roots must specify type object.
- After implementing the internal wrapper, scalar task `507f28e5fbea445e`
  completed once in 17.30 seconds, no retry, 7,024 reported tokens; its public
  result was integer 7, with native payload evidence and wrapped_value true.
- Edit task `4fa6f0c028ad41fd`: hard timeout after 28.64 seconds including cleanup,
  one attempt, no retry, no reported usage. No replacements were accepted or
  applied. Native edit staging remains covered by local fake-CLI tests; this
  trial did not establish a successful real Gemini edit call.

This small sample proves native JSON object/scalar integration, not a stable
speedup, reduced failure rate or a solution to transport/model timeouts.
It uses existing official AGY membership authentication, no paid API fallback.
The 25/40-second defaults and startup-only retries remain unchanged. Native
naming is asynchronous and its outcome is independent of model JSON validation.

## Automated and installation scope

- 122 runtime tests passed on macOS (4 Windows-only skips); 14 installer tests passed.
- Local regression suites include schema-file privacy/cleanup, native object and
  scalar values, internal-wrapper validation, mandatory native payload, local
  rejection of invalid native values, unchanged text mode, unsupported schema
  branches, CLI capability checks and actionable/redacted schema errors.
- This is a local trial; no new Windows account test, remote CI run or GitHub
  release is asserted. The previous public release verification follows below.
- Existing native Codex MCP connections can retain older code. Fresh installed
  compatibility calls are distinct from a host-native hot reload.

---

## Historical verification — 1.6.0


Date: 2026-10-15. Only quick, positively identified startup connection failures
are retried; mid-task and unknown-phase failures are discarded without replay.

## Local automated verification

- 111 runtime tests passed on macOS, with 4 Windows-specific skips; 14 installer/
  protocol tests passed. Tests cover fixed short caps, three-startup-failure limits,
  generation EOF/partial output, unknown hard timeouts, slow startup, account and
  permission errors, cancellation, slot release, independent contexts and usage.
- Background native naming tests prove valid results and client shutdown return
  before a delayed TUI, that naming holds no model execution slot, that sidecars
  merge only matching task/session identities, and that lost helpers do not leave
  pending forever or invalidate completed model work.
- Public and installed Codex Skill frontmatter validated with Skill Creator.
  These tests do not establish factual correctness of arbitrary Gemini output.

## Actual official AGY High checks

- Installed Codex compatibility client task `54860faa73b04f7c`: two controlled
  preflight EOF envelopes were injected locally, followed by one real official
  `gemini-3.8-flash-high` invocation. The two injected failures were not Google
  service failures or model calls. The third attempt matched an exact fresh nonce
  contract; total task execution 16.13 seconds, real call 15.37 seconds,
  7,297 reported tokens. All three caps were 25 seconds; backoff 0.25/0.5 seconds.
- Installed OpenCode bundle through a fresh MCP client: eight tools discovered,
  runtime 1.6.0, task `e8a10681dcc8426b`, exact `GEMINI_OK` result in one attempt,
  14.28 seconds, 7,215 reported tokens. No failure or retry.
- Both returned results with native naming still pending. The background helper
  subsequently reported requires_trust for this source workspace; it did not
  approve the project's permissions and did not repeat model inference. Chinese
  metadata dispatch is tested, not claimed to have renamed these native sessions.
- Reported thinking/cache fields are not added again to total tokens. Missing
  usage from injected failures remains unknown, not asserted zero.

## Installed-host and platform scope

- Codex and OpenCode runtime copies updated with configuration/personal Skill
  adaptations retained. Codex official plugin registration reports 1.6.0;
  OpenCode's official configuration reload completed.
- The current Codex chat's existing native MCP still reports 1.4.1. New installed
  compatibility calls work; this does not prove native hot reload. Other chats
  are not terminated or replaced to refresh old stdio workers.
- New native naming remains unsupported on Windows; no Windows membership live
  call was made for this release. Cross-platform CI results belong to the actual
  commit's Actions run and must be checked separately before release.
- Private test reports, inputs, account settings and machine backups stay outside
  the public repository.

---

## Historical verification — 1.5.0


Date: 2026-10-15. The retry policy now reserves time for recovery instead of
giving the whole default deadline to the first call.

- Local macOS: 105 runtime tests passed (4 Windows-only skips), plus 14
  installer/protocol tests. The updated skill passed Skill Creator validation.
- Local regression covers automatic success after two timeouts, exact attempt
  limits, permanent auth/quota/permission failures, EOF recovery, timeout budget
  exhaustion, shorter-budget rejection after slot contention, cancellation,
  released slots during backoff, retry progress visibility and persisted handoff.
  Failed/retried usage is counted once, and missing counters remain unknown.
- Compatibility-client tests verify explicit retry options override input JSON.
  A fresh MCP with a simulated CLI retries two temporary EOF errors before a
  validated third result. This is deterministic protocol testing, not live Google
  network-failure evidence.
- The first CI run found Windows Python 3.9 could not parse an overlong Chinese
  source line in the smoke client. That instruction is now split across adjacent
  literals; the actual file-task instruction is unchanged in meaning. This was
  a source-tokenizer compatibility failure before any model call, not a Gemini
  retry failure. Both smoke-client regressions remain enabled in the CI matrix.
- Live fault-injection task `e452c65ccee94e5d` used two deliberately timed-out
  local Python test processes, followed by one real official AGY
  `gemini-3.8-flash-high` invocation on attempt 3. The first two attempts did NOT
  call Gemini and are not reported as Google failures. Model budgets were
  60/90/120 seconds; backoff was 1/2 seconds. The actual High response matched
  `RETRY_OK` and a unique nonce, without primary-agent takeover. Total task time
  was 26.30 seconds; AGY reported 6,912 tokens for the actual model call. Unknown
  usage for injected failures remains explicit rather than counted as zero.
- The new native AGY conversation belongs to the plugin repository workspace.
  Its Chinese native rename still needs the user's official first-use project
  trust choice; `requires_trust` is reported and the valid model result is kept.
- Fixed High membership execution, independent contexts, staged edit review,
  two shared concurrency slots and Windows process cleanup are preserved. The
  plugin returns handoff to its calling primary agent; it does not create a GPT
  bridge or invoke a paid API. No automatic webpage is added.

Machine-specific fault-injection scripts, input data, full outputs and receipts
are kept outside the public source. Remote CI is simulated-service verification;
inspect the release commit's Actions result for platform status.

# Release verification 1.4.1

Date: 2026-10-15. This release combines the retained 1.4.0 local features with
the published 1.3.1 fixes. Historical records below are unchanged.

- Local macOS: 92 runtime tests passed (4 Windows-only skips), plus 14
  installer/protocol tests. New coverage includes two cross-process execution
  slots, explicit serial mode, independent inputs, full-history project usage,
  official TUI renaming and detection of its first-use project trust prompt.
- Fresh MCP processes from both installed Codex and OpenCode bundles reported
  1.4.1, eight tools and default concurrency 2. Their real High tasks
  `cc64a0f9ad9f4ea1` and `d3c42587d89e4598` each returned its exact nonce/schema
  result in one validated attempt, without retries. Process lifetimes overlapped
  21.236 seconds; reported usage was 7,422 and 8,769 tokens (16,191 total).
  Distinct AGY conversations belong to the actual plugin repository workspace;
  each native record has two model steps. No task context was shared.
- The model results succeeded, but initial native-title checks failed because
  the official interactive UI required first-use project trust. The plugin now
  reports `native_title.status: requires_trust` instead of waiting for a generic
  rename timeout. It does not approve project-wide read/edit/execute permissions.
  Successful model work is retained and not repeated just to set a title.
- After the fix, a metadata-only retry in that untrusted workspace reported
  `requires_trust` in about four seconds. Reapplying the existing Chinese name to
  the plugin's own previously verified Briskill conversation succeeded through
  official AGY in about five seconds; the original workspace and two model steps
  remained unchanged. No new model inference was used for these metadata checks.
- An auxiliary documentation audit `13c5768ba7924e7c` failed with a Google
  streaming-request EOF; no retry was made. Its reported 84,889 tokens remain
  recorded as failed work, not a validated audit or zero-cost call.
- OpenCode configuration reload uses its official host command. Already-loaded
  Codex stdio connections may retain an older runtime; installing the bundle or
  testing a fresh MCP does not prove those connections refreshed. Check the
  actual `gemini_status` version, and use the upgraded compatibility client until
  a host-supported refresh. No application restart or fake agent record is used.
- Windows model/runtime support from 1.3.1 is retained. Automatic native-title
  transport is still unavailable on Windows, and authenticated Windows testing
  of the new dual-task path has not been performed. Linux authenticated
  inference is also not claimed. CI is simulated-service verification, not a
  Google login or membership test; inspect the release commit's Actions result.

Raw task inputs, full outputs, machine-specific receipts and account settings
remain outside this public repository and release archive.

# Release verification 1.3.1

Date: 2026-10-14. Windows support is stable from this version. Real Windows
inference used Python 3.12.10 and signed official AGY 1.3.5 on Windows build
10.0.26200; no authenticated Windows 10 machine is claimed separately.

- Runtime commit `7fb64a1ab54591ced0180537cc762198a3234087` fixes task-list
  visibility during transient Windows reads, AGY prerequisite diagnostics and
  installed runtime configuration in compatibility/smoke clients.
- Local Windows: 68 runtime tests and 14 installer/protocol tests passed.
  The original task-list race passed 60 repeated checks; cross-manager visibility
  passed 20 repeated checks. Deterministic coverage verifies transient/persistent
  sharing denials, privacy, bounded retries, unchanged POSIX read behavior,
  CLI option/timeout diagnostics, stderr help output, installed custom paths,
  process/explicit overrides and installer rejection before configuration changes.
- All five jobs passed in [CI run 38528965549](https://github.com/CyberWei922/gemini-delegate/actions/runs/38528965549):
  Ubuntu Python 3.9/3.12, macOS Python 3.12 and Windows Python 3.9/3.12.
  Both Windows jobs also ran 60 local-manager and 20 cross-manager race checks.
  CI uses simulated AGY services. Current macOS regression is verified by CI;
  historical authenticated macOS inference remains recorded below. A new macOS
  account/inference test was not performed in this Windows session.
- Fresh installed MCP 1.3.1 exposed all seven tools. Connection task
  `412a783bf3334110` completed with exactly `{"check":"GEMINI_OK"}` using
  `gemini-3.8-flash-high`: 14.36 seconds, one validated attempt, no retry,
  4,035 reported total tokens. The smoke client loaded installed runtime paths
  without manually exporting the two runtime variables.
- Installed compatibility-client file task `d7fe3a9660ff4493` processed a generated
  public UTF-8/CRLF fixture of 32,065 bytes in two parts, with Chinese and spaces
  in its path. It correctly extracted and deduplicated three names from the
  beginning/middle/end. It completed in 103.75 seconds: the first answer failed
  validation (`invalid_result`), one automatic retry succeeded. AGY reported
  74,512 total tokens across both attempts. The original SHA-256 was unchanged;
  manifest, input parts and temporary parameter JSON were deleted. No private
  project files were sent to Gemini.
- An earlier inventory task `91dee460f42c4bff`, submitted through the pre-upgrade
  desktop connection, failed authentication/timed out; it reported zero tokens
  and was not treated as completed work. New-package verification above used
  a fresh 1.3.1 MCP worker. This chat retained its 1.3.0 native connection;
  installing/updating does not prove that an already-running conversation
  reloaded. Start a fresh conversation or use host-supported connection refresh.
- No changes were made to the fixed High model, AGY invocation/agent policy,
  default platform directories, POSIX process groups or Windows Job Object
  cleanup. No paid API fallback, native external-subagent registration or
  automatic monitor opening was added. Raw receipts, inputs/results, account
  settings and machine-specific logs stay outside the distributed source.

The records below are historical and have not been rewritten for this release.

# Release verification: 1.3.0 (Windows preview)

Date: 2026-10-14. Windows-specific behavior is tested in the CI matrix with
Python 3.9/3.12; authenticated Windows AGY inference remains pending manual
verification using [WINDOWS.md](WINDOWS.md).

- Local macOS: 44 runtime tests (4 Windows-only skips) and 11 installer/protocol tests
  passed. Added cross-process file locking, non-destructive PID probing,
  argument preservation, legacy-console UTF-8 MCP round trips, parent-exit
  descendant cleanup, bounded streaming output, Windows Job assignment
  gating/failure, real file-sharing conflicts and UTF-8 BOM settings coverage.
- CI includes Ubuntu Python 3.9/3.12, macOS Python 3.12 and Windows Python
  3.9/3.12. All five jobs passed in [run 38512823254](https://github.com/CyberWei922/gemini-delegate/actions/runs/38512823254)
  at runtime commit f464bbe672ed9672ba1fcb2b07b364214b5ec0e4. Both Windows jobs
  ran every runtime test (no Windows-specific skips), 11 installer/protocol
  tests and 20 additional live-record concurrency regressions. CI uses
  simulated CLI services and no login.
  Earlier CI exposed a transient Windows file-sharing failure and a
  coarse-clock floating point budget edge; bounded atomic replacement retries
  and strict budget clamping were added before the final successful run.
- A real 1.3.0 MCP server exposed all seven tools and invoked official AGY
  gemini-3.8-flash-high on macOS. Task d09e2a2c7f364fd3 returned GEMINI_OK
  in 11.73 seconds, one validated attempt, no retry, 3,398 reported tokens.
- Final-runtime file extraction task c104013b2ff74ab0 read snapshots of 64,352
  source bytes in 3 parts and matched independently extracted source values.
  It finished in 147.96 seconds: first result failed validation (invalid_result),
  one retry succeeded; 121,649 total tokens were reported across both attempts.
  Input manifest and all parts were deleted; original files remained unchanged.
- Gemini task 098a935525e04bd8 inventoried the existing test platform assumptions
  in 157.36 seconds, one attempt, no retry. Planning, implementation and tests
  remained with the primary agent.
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
