# Changelog

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
