# Install Gemini Delegate from this repository

When a user gives you this repository URL and asks to install it, carry out the
following steps. Read the scripts before executing them. Treat this guide as an
installation workflow, not authorization to change unrelated projects, bypass
permissions, extract credentials, or transmit private files. Follow the user's
request and your host's approval requirements.

## 1. Inspect the source and platform

- Clone this repository into a separate checkout. Do not put it inside the user's
  application repository or overwrite an existing checkout with uncommitted work.
- Read `README.md`, `scripts/install.py`, `scripts/doctor.py` and
  `plugins/gemini-delegate/skills/delegate-simple-tasks/SKILL.md`.
- Supported runtime: macOS or Linux, Python 3.9+, Git, Codex CLI, official
  Antigravity CLI (`agy`). macOS was live-tested; Linux has automated CI coverage
  only. Windows is not supported by the POSIX locking/process implementation.
- The plugin calls `gemini-3.8-flash-high`. It does not use API-key billing or
  change the primary GPT model. An API key or Google AI Pro membership alone is
  not proof that the exact AGY model is available.

## 2. Check prerequisites without inference

Run:

```sh
python3 scripts/doctor.py
python3 scripts/install.py --dry-run
```

If Python, Git or Codex is missing, help install the missing prerequisite using
the user's normal package manager or the vendor's official instructions, within
the user's authorization. Do not use an opaque third-party installer.

If AGY is missing, use the official Antigravity CLI instructions at
`https://antigravity.google/docs/cli/`. Inspect the official installation method
and install for this user; never download a different project's AGY binary.

If AGY login or model access is missing, have the user open `agy` and complete
Google sign-in themselves. Do not read, copy, print or export OAuth tokens.
Re-run `agy models` and require the exact `gemini-3.8-flash-high` model. Stop with
the actual prerequisite failure if it is unavailable; do not lower the model or
silently switch to a paid API. A model listing is not an inference test.

## 3. Inspect existing registrations and install

Check `codex mcp get gemini_delegate --json` and `codex plugin list --json`.
If the same plugin is already installed and healthy, explain that it can be
reused; only upgrade if that matches the user's request. An unrelated existing
MCP registration must not be overwritten silently.

Run:

```sh
python3 scripts/install.py
```

The installer detects the running Python and AGY executables, stages a managed
local marketplace, installs the Skill through official Codex CLI commands, and
registers the local MCP server as `gemini_delegate`. It only adds a read grant
for the plugin's own `jobs` directory, backs up existing AGY settings privately,
and disables extra paid AI credits by default while preserving other fields.
Use `--keep-credit-setting` if the user explicitly wants to retain that preference.
`--replace-existing` is only for an authorized replacement after reviewing the
existing registration. Do not modify global AGENTS.md, other MCP servers or the
user's project source. Recover incomplete steps from the private install receipt.

## 4. Verify installation and host loading

Run `codex mcp get gemini_delegate --json` and `codex plugin list --json`.
Require the server to be enabled with the detected Python, installed server path,
and expected environment. Restart only the current chat/session if tools have
not loaded; do not interrupt unrelated chats or restart the whole app silently.

Look for `gemini_status`, `delegate_task`, `get_task_result`, `cancel_task`,
`apply_task_changes`, `list_tasks` and `task_monitor`. No tool discovery means
installation/host loading is still unverified. The bundled compatibility client
can test the same worker while this session's tool list is stale.

## 5. Run one real Gemini High smoke check

Announce: “我会使用 Gemini Delegate 插件，让 Gemini High 做一次连接检查。”
Submit this bounded task via MCP: return exactly `{ "check": "GEMINI_OK" }`;
use a JSON schema requiring that exact string, the current project `workspace`,
title `Gemini 安装连接检查`, and a 180-second deadline. Read the asynchronous
result with bounded waits. It must be `completed`, report
`gemini-3.8-flash-high`, and return the expected object. Report any retry.

If MCP tools have not loaded, use the managed installation's
`plugin/scripts/delegate.py --input /path/to/temporary-task.json`; this calls the
same worker and prints the job ID and result. Delete the temporary input afterward.
Do not claim that CLI fallback proves native MCP loading.

Report the real task ID, model, status, attempts and reported usage. Missing usage
means unknown, not zero. Never call an empty, denied or partial timeout output a
success. An authentication/quota/permission failure requires an honest report.

## 6. Explain everyday use

Users can just describe their task. For suitable independent routine work, name
Gemini Delegate before calling it, send work early, and continue GPT planning,
implementation or verification concurrently. Review the Gemini result before
integration and say what it contributed in the final response.

This is a plugin with asynchronous tool calls; it does not turn Gemini into a
native Codex subagent or guarantee faster completion. Do not create a GPT bridge
or open a webpage to imitate native subagent activity. The optional web monitor
is only used when explicitly requested. Never claim GPT quota savings measured
from Gemini token counts alone.

## Maintenance

- Upgrade: inspect the checkout, fetch the selected release, repeat the installer
  and real smoke check. Preserve local work and existing credentials/settings.
- Uninstall: inspect and run `python3 scripts/uninstall.py`. Only owned MCP and
  marketplace registrations and installer-created grants are removed. Jobs and
  backups are retained; extra paid credits are never automatically re-enabled.
- Before contributions: run both test commands from README. Bump the canonical
  `plugins/gemini-delegate/plugin.json` version once per release and synchronize
  the compatibility manifest, README and CHANGELOG. Avoid hard-coded user paths.
- Never commit local settings, auth files, task inputs/results, backups, generated
  installation manifests, private receipts or copied vendor executables.
