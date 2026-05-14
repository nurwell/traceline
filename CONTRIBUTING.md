# Contributing

TraceLine is intentionally small and local-first. Contributions should keep the
tool predictable, safe, and easy to run without services.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

## Guidelines

- Keep changes small and focused.
- Add tests for parser, redaction, storage, and CLI behavior changes.
- Do not add network-dependent tests.
- Avoid new dependencies unless the standard library and existing dependencies
  are not enough.
- Never include real logs containing secrets or personal data in fixtures.
- Prefer deterministic behavior over guesswork.

## Parser Contributions

When adding a parser:

1. Add focused unit tests with realistic but synthetic log lines.
2. Report skipped lines through `traceline diagnose`.
3. Preserve UTC normalization.
4. Avoid parsing message text with broad patterns that can create false positives.
