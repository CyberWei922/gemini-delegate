# Changelog

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
