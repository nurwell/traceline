# Changelog

## 0.1.0

- Initial local-first TraceLine CLI.
- Ingest timestamped logs into a local JSONL store.
- Merge events into a UTC incident timeline.
- Search, inspect, summarize, and export events.
- Redact common secret shapes before storage by default.
- Support Markdown, JSON, CSV, and HTML exports.
- Support pipeline ingestion with `traceline from-stdin`.
- Join common stack trace continuation lines with their timestamped event.
- Add `traceline analyze` for one-command analysis of real log files without store setup.
- Infer source labels from filenames when `add` or `analyze` runs without `--source`.
- Add `traceline run` as the short product command for immediate local analysis.
- Add `tl` as the shortest command for direct local log analysis.
- Add short flags `--tz` and `--out` for everyday usage.
- Infer report format from `-o` file extensions such as `.html`, `.json`, and `.csv`.
- Accept directories and include common log-like files automatically.
- Print a `diagnose` suggestion when parsing skips lines.
- Show redacted skipped-line examples in `diagnose`.
- Add `--version` to `tl` and `traceline`.
- Improve HTML reports with summary metadata and a redaction notice.
- Move sample inputs to `examples/logs` and sample outputs to `examples/reports`.
