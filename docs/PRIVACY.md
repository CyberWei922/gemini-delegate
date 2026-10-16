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

## 1.7.0 输入与进度

显式文件内容、上下文和公开来源整理成一个 UTF-8 提示，通过 stdin 交给官方 AGY；不进入命令行参数，
不要求模型逐轮读取任务清单和分块。执行结束释放输入快照，原生输出 Schema 临时文件删除。
流式事件仅保留阶段、时间、事件／步骤计数、工具名称和已报告用量；不保存或回传中间正文、思考内容、
工具参数与工具输出。成功结果、失败诊断、备份及官方 AGY 自身的存储仍按原有机制保留。
中断时可用步骤用量标为部分记录；与终态累计用量不会重复计算。
