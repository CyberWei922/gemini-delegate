# Changelog

## 1.5.0 — 2026-10-15

- Retry recoverable Gemini failures automatically: three total attempts by default, bounded by one 300-second deadline and growing 60/90/120-second call caps.
- Expose max_attempts (1–5), explicit initial caps, cancellable backoff, terminal handoff and per-attempt evidence; never retry account/permission/quota failures blindly.
- Skip intermediate failed-attempt naming so retries can proceed; retain independent contexts, native IDs and reported/unknown usage.
- Teach the primary agent to wait on the same retrying task and take over only after automatic recovery stops. Verification scope is in the repository's docs/VERIFICATION.md.

## 1.4.1 — 2026-10-15

- Publish retained two-task concurrency, native project sessions/Chinese titles and project token accounting with independent model contexts.
- Merge upstream 1.3.1 Windows visibility, AGY prerequisite checks and installed runtime configuration fixes.
- Apply explicit/process/installed/default precedence to concurrency as well as AGY/state paths.
- Clarify native title outcomes; Windows automatic native renaming remains unsupported.
- Detect the official first-use project trust prompt without approving project-wide permissions or misreporting a generic timeout.
- Local macOS: 92 runtime tests (4 Windows-only skips) and 14 installer/protocol tests passed. Live/CI scope is recorded in the repository verification document.

## 1.4.0 — 2026-10-15

- Retain the validated native workspace/title, project accounting and independent context features.
- Default AGY concurrency is now 2, with explicit 1 still supported.
- Upgrade the existing local installation and preserve user configuration; use the new compatibility client when a chat's MCP is stale.
- 66 runtime tests (4 Windows-only skips on macOS) and 11 installer/protocol tests passed.
- Installed-runtime live verification is recorded in the private upgrade receipt; Windows native title transport remains unavailable.

## 1.4.0-preview.2 — 2026-10-15（本地试验，未发布）

- Start official AGY model calls in the actual project workspace; private input snapshots stay separate.
- Discover the restricted worker through the official global agents directory; preserve conflicting configurations.
- Set native Chinese titles through a ready official TUI's /rename and /exit with shared slots and bounded cleanup.
- No print-mode rename, no startup-prompt rename, no native storage writes; Windows interactive rename remains unsupported.
- 66 runtime tests (4 Windows-only skips), 11 installer/protocol tests. Two real High tasks each succeeded once;
  overlapping calls 16.35s, 11,911 reported tokens. Native records confirmed project paths, exact Chinese titles,
  distinct IDs and 2 steps each (no additional model turn for rename).

## 1.4.0-preview.1 — 2026-10-15（本地试验，未发布）

- Opt-in two-call AGY execution with shared cross-process slots; serial remains the default.
- Project usage_summary includes all recorded tasks/retries, readable work names and real returned AGY conversation IDs.
- Independent per-attempt contexts, compact totals, explicit unknown usage and non-overwriting JSON export.
- macOS: 56 runtime tests (4 Windows-only skips), 11 installer/protocol tests; two real Gemini High calls validated,
  no retries, 17.06 seconds of overlapping process lifetimes and 9,948 reported total tokens.
- Production installation unchanged pending user review; no new Windows account or remote CI verification.

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

- Added portable public packaging, MIT licensing and repository installation
  guidance with dynamically detected Python/AGY paths.
- Added runtime state/AGY environment overrides for managed installations.
- Public installer, CI and verification scope are documented at repository root.

## 1.1.1 — 2026-10-14

- Made named pre-call announcements and asynchronous cooperation the default
  Skill workflow, with explicit Gemini work and concurrent primary-agent work.
- Added dependency-aware waits and final attribution; corrected compatibility
  client instructions and removed routine native-panel discussion.
- Verification: live MCP submission and completion, an interleaved instruction
  update, three reviewed Chinese notice examples, and package/source checks.
  Runtime code and Briskill application files were unchanged.

## 1.1.0 — 2026-10-14

- Added live atomic task records, explicit titles and project-scoped list_tasks,
  with execution states, retries, elapsed time, reported usage and bounded results.
- Added a compatibility client for chats with stale MCP tool catalogs, plus
  interruption detection and applied-change indicators.
- Added an optional read-only local web monitor. After the user's clarification,
  removed all automatic web opening/startup and GPT bridge instructions. Native
  direct-Gemini activity-list integration remains unverified and unavailable
  through this chat's exposed subagent interface.
- Verification: 18 automated tests cover existing execution/edit safeguards,
  live records, preview privacy, monitor authentication and recovery. A real
  direct Gemini High call returned the three requested Chinese status labels in
  13.35 seconds, one attempt. No Briskill application code was changed.

## 1.0.0 — 2026-10-13

- Added Gemini High delegation through the official AGY CLI and reusable task
  routing instructions, preserving primary GPT planning and judgment.
- Added asynchronous task status, cancellation, serialized AGY execution,
  deadlines, bounded retry, and complete result/schema validation.
- Added public read-only web retrieval and optional existing Agent Reach/Exa
  search, avoiding global AGY browsing grants.
- Added explicit local input files, staged edits, conflict detection and backups.
- Validation scope and actual results are recorded in VALIDATION.json.
