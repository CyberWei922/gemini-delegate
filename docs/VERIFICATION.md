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
