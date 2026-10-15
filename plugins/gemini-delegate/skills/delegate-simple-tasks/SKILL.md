---
name: delegate-simple-tasks
description: Use when day-to-day work has independent routine parts that can run alongside the primary GPT agent: source collection, web research, file/code inventories, text/data transformations, and specified mechanical edits. Announce Gemini Delegate by name, submit asynchronous Gemini 3.8 Flash High work through official AGY, and continue GPT planning and judgment while it runs. High is the fixed default; respect the installing user's explicit budget and privacy preferences.
---

# Gemini Delegate

Use the gemini-delegate MCP tools for appropriate bounded work without asking the
user to reconfirm their established delegation preference. Use Gemini membership quota for useful delegated work within the user's task scope. Prioritize correct results and reduced GPT work; respect explicit
quota limits. Keep user instructions and applicable repository/skill rules in force.

## Responsibility

The primary GPT agent owns goals, decomposition, plans, architecture, complex
logic, risk/permission judgments, root-cause conclusions, and final integration.
Gemini High performs the simple executable parts: collect official source facts,
read documents/source files, inventory code, extract/translate/rewrite supplied
text, transform data, and implement explicitly specified routine replacements.
Do not outsource unresolved design decisions, sensitive credentials, production
deployment, Git pushes, communications to people, or arbitrary shell autonomy.

Delegate early, before reading large low-level material yourself. Send only the
task data and constraints needed, including relevant AGENTS.md requirements as
explicit constraints when code edits are delegated. The worker does not inherit
this conversation or repository rules. Do not ask it to choose the project plan.
Respect dedicated artifact skills (images, spreadsheets, documents, etc.); this
worker assists their bounded preparation rather than substituting their required
tools or verification workflows.

## Execute

Default to visible, asynchronous plugin cooperation when there is useful
independent work. Before the actual delegate_task call, say one concise sentence
in the user's language naming Gemini Delegate, the bounded work for Gemini High,
and what the primary agent will do concurrently. For example:
“我会同时使用 Gemini Delegate 插件，让 Gemini High 整理资料；我继续制定方案。”
Only announce work that you then really submit; do not use the announcement as a
substitute for a tool call. Do not promise that every task will finish faster.

delegate_task returns an asynchronous job ID. Dispatch early, then continue
useful independent planning, implementation, verification or integration work in
the main agent. Do not immediately block on Gemini while independent work is
available, and do not redo the same delegated processing in GPT. Read results
when their dependent step is ready; use bounded waits of at most 20 seconds.
Never proceed with a decision or write that depends on a result before it arrives.
If there is no meaningful independent work, explain that the Gemini result is
needed next and wait honestly rather than claim parallel execution. AGY jobs are
bounded to two independent calls by default across processes sharing one state
directory; explicit concurrency 1 remains available. Check
gemini_status.max_concurrent_agy_calls rather than assuming a queued job is
already executing. GPT can continue independent work under either setting.

At the start of a chat or after an upgrade, check gemini_status once. If the
loaded plugin_version is older than this bundle's plugin.json or lacks native
workspace/title support, use this installed bundle's scripts/delegate.py for
new work and usage queries. A successful compatibility call does not prove that
the chat's old native MCP process has reloaded. Never kill or reload other chats
to refresh a stale connection.

Announce the actual task sent to Gemini High, give it a concise Chinese title,
and pass the real project workspace. Use the Gemini MCP tools or bundled CLI
client directly. The worker runs Gemini through AGY, without a GPT bridge agent.
Report the Gemini job ID, exact model, validated output and any failure/retry.
If asked whether a project used Gemini, read list_tasks with that exact workspace.
Missing records only mean no delegation through this plugin, not no possible
Gemini usage outside it.

Use ordinary plugin tool activity as the visible invocation. Native Gemini
subagent selection was actually rejected by this chat's spawn_agent interface.
Do not manufacture native entries, label GPT agents as Gemini, or spawn a GPT
bridge just to obtain a card. Do not reopen the native-panel issue during routine
plugin use unless the user asks. Do not automatically open a webpage;
task_monitor is explicit opt-in only.

If the current desktop session has not loaded the MCP tools, use the bundled
`scripts/delegate.py` compatibility client with Python, resolved relative to
this plugin directory. `--monitor --workspace /absolute/project` returns the
optional monitor URL only when explicitly requested; `--list` reads real task records; `--input /path/task.json`
accepts the delegate_task argument object, prints the submitted job ID immediately,
then waits for the validated result. Run it through a yielded
exec session and poll completion. Keep task JSON
temporary and delete it after use. This is the same
worker and evidence trail, not a different model or paid API fallback.

1. Use `gemini_status` if backend availability is uncertain.
2. Call `delegate_task` with an explicit instruction. The model is fixed to
   `gemini-3.8-flash-high`; there is no silent fallback to another model.
   - Text/data tasks: supply `context`; use `response_type: json` plus a result
     schema when field names/counts matter. Set minItems=maxItems for exact batch
     coverage. Supported schema keywords are described by the tool.
   - Local files: supply `workspace` and explicit `input_files`. The plugin
     reads those files and gives the worker a small manifest with lossless,
     bounded UTF-8 text parts. Keep tasks narrow and request concise output;
     use 300–600 seconds when several large files must be read in High.
   - `timeout_seconds` bounds retrieval, shared-slot waiting and all attempts
     once execution starts. Default 180 seconds; no hidden per-call 75-second
     cap. `attempt_timeout_seconds` optionally caps the first call and permits
     a timeout retry only with a strictly longer remaining call budget.
   - Research: provide public `web_urls` or `search_query`. The plugin fetches
     public pages through a read-only adapter. Search uses the user's existing
     Agent Reach/Exa backend. It neither changes global AGY web permissions nor
     bypasses access controls or logged-in/private page restrictions.
   - Mechanical edits: use `response_type: edit` and explicit input files.
     Gemini returns replacements; originals remain unchanged until application.
3. Read `get_task_result`. Do independent work while it runs; wait at most 20
   seconds per call and avoid frequent polling. AGY concurrency defaults to two;
   respect explicit serial settings and actual backend failures. Keep individual tasks narrow and independently
   checkable; split big heterogeneous batches instead of endlessly retrying them.
4. Treat success as transport/schema validation, not proof of factual or code
   correctness. Review evidence URLs, extract counts, calculations, and relevant
   code differences. The worker cannot claim to have executed checks; the primary
   agent runs appropriate meaningful tests using its ordinary tools.
5. For authorized edits, inspect staged artifacts and call
   `apply_task_changes` with `reviewed: true`. It checks original hashes before
   writing and retains backups. A source conflict requires regenerating against
   the new file; never force an overwrite. Apply repository version/changelog
   rules once per delivery, under primary-agent control.
6. Summarize the Gemini contribution and whether it was completed, failed or
   cancelled. Mention retries when material. When asked, provide the real job ID,
   selected model and reported usage. Do not imply that reported Gemini usage is
   measured GPT savings or that a queued job has already called the model.
   Summarize useful results to the user. Do not paste large source dumps or
   re-read every input in GPT. If a result preview is truncated, use the provided
   local result artifact when completeness is needed.

## Failure and quota behavior

For usage questions, call usage_summary with the real workspace. It aggregates
all task records and retries without the task-list display limit. Default to
compact project totals; request include_tasks only for a named task/native ID
mapping. Missing attempt usage is unknown, not zero; do not add thinking or
cache counts again to total_tokens. Grouping is accounting only: every model
attempt stays independent and starts in the real project workspace, without
--continue/--conversation. On macOS/Linux the worker resumes ONLY its own native
ID in a ready official TUI to execute /rename and /exit; this is metadata, not
another model turn or shared history for a different task. Read native_title
status before claiming a native name was set; Windows currently reports
unsupported. AGY 1.3.5 print-mode /rename is unavailable and --prompt-interactive
/rename goes to the model; neither may substitute for the native command.
Token Monitor display/refresh still requires actual observation.
Never change other chats' concurrency or reload them to run a local trial.

The wrapper rejects nonzero exits, non-SUCCESS statuses, soft permission denials,
empty results, partial timeout output, malformed JSON, schema/count mismatches,
unexpected file paths and stale originals. It uses both an AGY timeout and a hard
process-group deadline, and permits at most one retry on recoverable output
failures. Default full-budget timeouts are not blindly retried; an explicitly
capped first attempt can retry only with a longer budget, rechecked after slot
waiting. Validation retries include the specific error. No model downgrade occurs. A failed result must not be reported
as completed work. Cancel unneeded tasks with `cancel_task`.

If authentication, quota, search connectivity or a permission fails, identify the
actual failure. Continue the bounded task in GPT when appropriate; do not spin
on exhausted Gemini quota or switch to paid API billing. Use the existing
official AGY account login; never extract OAuth tokens or call private endpoints.
Additional paid-credit usage remains disabled independently of membership quota.
