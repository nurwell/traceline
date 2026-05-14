# Security Policy

TraceLine works with local logs, which may contain secrets or personal data.

## Local-First Behavior

- TraceLine does not upload logs.
- TraceLine does not call an external service.
- TraceLine writes reports only when an output path is provided.
- The persistent store, when used, defaults to `.traceline/events.jsonl`.

## Redaction

Secret redaction is enabled by default during ingest and analysis. Current rules
cover common shapes such as bearer tokens, basic auth headers, cookies, API keys,
JWT-like values, passwords, and database URLs.

Redaction is best-effort. Review reports before sharing them.

## Reporting Security Issues

Do not open a public issue with raw logs, secrets, tokens, or credentials.

If this project has a private security advisory channel enabled on GitHub, use
that channel. Otherwise, open a minimal public issue that describes the class of
problem without including sensitive data.
