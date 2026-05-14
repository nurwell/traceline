# TraceLine

[![CI](https://github.com/nurwell/traceline/actions/workflows/ci.yml/badge.svg)](https://github.com/nurwell/traceline/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TraceLine turns raw local logs into a shareable incident timeline in one command.

It is for developers, support engineers, and small teams who need to answer:
what happened, when did it happen, and which log file proves it?

TraceLine runs locally. It does not upload logs, call an external service, or
require an account. Secret redaction is enabled by default.

## Fast Path

Analyze real logs:

```bash
tl examples/logs
```

Write a report:

```bash
tl examples/logs -o incident.html
```

The output extension chooses the report format:

```bash
tl examples/logs -o incident.md
tl examples/logs -o incident.json
tl examples/logs -o incident.csv
```

Analyze specific files:

```bash
tl app.log nginx.log deploy.log -o incident.html
```

TraceLine includes `.log`, `.txt`, `.out`, `.err`, `.json`, and `.jsonl` files
from the directory.

If logs use local timestamps without an offset, set the timezone:

```bash
tl app.log nginx.log --tz Europe/Warsaw
```

TraceLine uses each filename stem as the source label. For example, `app.log`
becomes `app`. Override labels when filenames are unclear:

```bash
tl service.log access.log -s api -s edge
```

## What You Get

```text
Analyzed 3 files: 7 events, 0/7 skipped lines.
Incident timeline

57ca2a41f32a6e21  2026-05-13 14:02:11  deploy     unknown deploy started version=8f31a2
bcaf498af94e8542  2026-05-13 14:03:02  app        error   ERROR checkout-api payment timeout request_id=req_91
38e93363327f28af  2026-05-13 14:03:04  nginx      error   "POST /checkout" 504 upstream timed out
59c3062b4ac746f6  2026-05-13 14:03:07  app        error   ERROR checkout-api database pool exhausted request_id=req_92
dae42283c02f5ca1  2026-05-13 14:03:09  nginx      error   "POST /checkout" 502 bad gateway
869d7be12cb93623  2026-05-13 14:04:30  deploy     unknown rollback started version=7c21be
4810e542843072a9  2026-05-13 14:05:10  app        info    INFO checkout-api recovered
```

## Install Locally

From this repository, without downloading anything new:

```bash
uv run traceline --help
uv run tl --help
```

To install the local checkout as a command:

```bash
pipx install .
tl --help
```

If `pipx` is not available, keep using:

```bash
uv run tl app.log nginx.log
```

## Why Use It

Use TraceLine when raw logs are already on your machine and you need a clean
timeline before a handoff, postmortem, support reply, or AI-assisted summary.

It is not a replacement for Datadog, Splunk, Grafana, Sentry, or distributed
tracing. Those systems are better for live monitoring and long-term search.
TraceLine is the small local tool for quickly turning evidence into an artifact:

```bash
tl logs -o incident.html
```

## Commands

Most users need only these:

```bash
tl FILE_OR_DIR [FILE_OR_DIR ...]
tl FILE_OR_DIR [FILE_OR_DIR ...] -o incident.html
tl --version
traceline diagnose FILE
traceline redact FILE
```

Use a persistent local store when an investigation spans multiple steps:

```bash
traceline add app.log
traceline add nginx.log -s edge --tz Europe/Warsaw
traceline timeline
traceline search "timeout|rollback|502|504"
traceline first-error
traceline gaps --over 60
traceline export incident.md
```

Pipeline input:

```bash
journalctl -u checkout.service -o short-iso | traceline from-stdin -s systemd
traceline timeline
```

Full command list:

```bash
tl FILE_OR_DIR [FILE_OR_DIR ...] [-o REPORT] [-f markdown|html|json|csv]
traceline run FILE_OR_DIR [FILE_OR_DIR ...] [-o REPORT] [-f markdown|html|json|csv]
traceline analyze FILE_OR_DIR [FILE_OR_DIR ...] [-o REPORT] [-f markdown|html|json|csv]
traceline add FILE [-s SOURCE] [--tz TIMEZONE] [--no-redact]
traceline from-stdin [-s SOURCE] [--tz TIMEZONE] [--no-redact]
traceline timeline [-s SOURCE] [--level error] [--since TIME] [--until TIME]
traceline search REGEX
traceline first-error
traceline gaps --over 60
traceline inspect EVENT_ID
traceline sources
traceline stats
traceline diagnose FILE
traceline redact FILE
traceline export REPORT [-f markdown|html|json|csv]
traceline clear --yes
traceline --version
```

`tl` is the shortest product command. `traceline` is the full toolbox.

## Supported Logs

TraceLine parses events that start with:

- ISO timestamps: `2026-05-13T14:03:02Z`
- Space timestamps: `2026-05-13 14:03:02 UTC`
- Nginx/Apache timestamps: `13/May/2026:16:03:04 +0200`
- Apache bracketed timestamps: `[13/May/2026:16:03:04 +0200]`
- JSON logs with `time`, `timestamp`, `@timestamp`, or `ts`

It also joins common stack trace continuation lines to the timestamped event
above them.

If too many lines are skipped, run:

```bash
traceline diagnose app.log
```

## Safety

- Logs stay on your machine.
- Redaction is on by default.
- Reports are written only when `-o` or `--output` is passed.
- The default persistent store is `.traceline/events.jsonl`.
- `clear` refuses to delete the store unless `--yes` is passed.
- See [SECURITY.md](SECURITY.md) for the security policy.

Current redaction targets include:

- `Authorization: Bearer ...`
- `Authorization: Basic ...`
- `Cookie: ...`
- `token=...`, `api_key=...`, `secret=...`, `password=...`
- `X-Api-Key: ...`
- JWT-like values
- common database URLs

Redaction is a safety layer, not a guarantee. Review reports before sharing.

## Limits

- Events must start with a supported timestamp format.
- JSON parsing currently reads string timestamp and message fields only.
- Stack trace joining is conservative and targets common Python/JVM-style lines.
- TraceLine is not a log database, observability platform, or alerting system.

## Development

No network is required for normal local checks once dependencies are present:

```bash
uv run pytest
uv run ruff check .
uv build
```
