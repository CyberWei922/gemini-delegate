# Data flow

The plugin is a local process. It invokes the user's installed official AGY CLI
and existing Google account. Task instructions and supplied files/page text are
sent to the model through AGY. Google's and AGY's own terms and retention apply.
The repository does not supply a shared account, API key, hosted inference
service or telemetry endpoint.

The local task directory retains short titles, model/status/usage metadata,
results, evidence URLs and hashes, staged replacements and backups. Input
manifests and all raw text snapshot parts are deleted after execution. Timeout
diagnostics retain only timings, error codes and partial-output byte counts, not
the partial stdout/stderr contents. Original and staged file contents can remain
in the results/backups needed for applying edits. Progress previews are bounded;
edit previews omit full replacement contents. Do not send secrets or private
material unless you intend to send it to Google through your own account.

Optional public-page fetching accesses the supplied websites; the network safety
adapter may query Google's public DNS resolver to verify public addresses. Optional
search uses the user's separately configured Exa/mcporter backend. The installer
does not configure those accounts or collect their keys.

The optional read-only task monitor is local to 127.0.0.1, uses a random access
token and rejects foreign hosts/origins. It never opens automatically. Anyone
with local account access or the private URL may be able to view the bounded
records. Uninstall retains jobs and backups so the user can recover work.

AGY settings backups and the installation receipt are stored privately outside
the repository. Do not publish them. The installer changes only its own jobs read
grant and the declared extra-credit preference, preserving unrelated fields.
