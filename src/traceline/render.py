from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import UTC, datetime
from html import escape
from io import StringIO

from traceline.models import Event


def render_timeline(events: list[Event]) -> str:
    if not events:
        return "No events found."

    lines = ["Incident timeline", ""]
    for event in events:
        lines.append(_format_event(event))
    return "\n".join(lines)


def render_markdown(events: list[Event]) -> str:
    lines = [
        "# Incident Timeline",
        "",
        "| ID | Time UTC | Source | Level | Event |",
        "|---|---|---|---|---|",
    ]
    for event in events:
        timestamp = _format_timestamp(event.timestamp)
        message = event.message.replace("|", "\\|")
        lines.append(f"| {event.id} | {timestamp} | {event.source} | {event.level} | {message} |")
    return "\n".join(lines) + "\n"


def render_json(events: list[Event]) -> str:
    payload = [event.model_dump(mode="json") for event in events]
    return json.dumps(payload, indent=2) + "\n"


def render_csv(events: list[Event]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["id", "timestamp_utc", "source", "level", "message", "file", "line_number"],
    )
    writer.writeheader()
    for event in events:
        writer.writerow(
            {
                "id": event.id,
                "timestamp_utc": _format_timestamp(event.timestamp),
                "source": event.source,
                "level": event.level,
                "message": event.message,
                "file": event.file,
                "line_number": event.line_number,
            }
        )
    return buffer.getvalue()


def render_html(events: list[Event]) -> str:
    generated_at = _format_timestamp(datetime.now(UTC))
    source_counts = Counter(event.source for event in events)
    level_counts = Counter(str(event.level) for event in events)
    first_error = _first_error(events)
    source_summary = ", ".join(
        f"{escape(source)}: {count}" for source, count in sorted(source_counts.items())
    )
    level_summary = ", ".join(
        f"{escape(level)}: {count}" for level, count in sorted(level_counts.items())
    )
    first_error_summary = (
        f"{escape(_format_timestamp(first_error.timestamp))} "
        f"{escape(first_error.source)}: {escape(first_error.message)}"
        if first_error is not None
        else "No error-like events found."
    )
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(event.id)}</td>"
        f"<td>{escape(_format_timestamp(event.timestamp))}</td>"
        f"<td>{escape(event.source)}</td>"
        f"<td>{escape(event.level)}</td>"
        f"<td>{escape(event.message)}</td>"
        "</tr>"
        for event in events
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TraceLine Incident Timeline</title>
  <style>
    body {{ color: #1f2933; font-family: system-ui, sans-serif; margin: 2rem; }}
    .summary {{
      display: grid;
      gap: 0.75rem;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      margin: 1rem 0 1.5rem;
    }}
    .summary div {{
      background: #f7f9fb;
      border: 1px solid #d9e2ec;
      padding: 0.75rem;
    }}
    .summary strong {{ display: block; margin-bottom: 0.25rem; }}
    .notice {{ color: #52606d; margin-top: 1.25rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 0.45rem; text-align: left; vertical-align: top; }}
    th {{ background: #f4f4f4; }}
    td:nth-child(5) {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      white-space: pre-wrap;
    }}
  </style>
</head>
<body>
  <h1>Incident Timeline</h1>
  <section class="summary">
    <div><strong>Events</strong>{len(events)}</div>
    <div><strong>Sources</strong>{source_summary or "none"}</div>
    <div><strong>Levels</strong>{level_summary or "none"}</div>
    <div><strong>First Error</strong>{first_error_summary}</div>
    <div><strong>Generated UTC</strong>{escape(generated_at)}</div>
  </section>
  <table>
    <thead><tr><th>ID</th><th>Time UTC</th><th>Source</th><th>Level</th><th>Event</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  <p class="notice">
    Generated locally by TraceLine. Secret redaction is best-effort; review before sharing.
  </p>
</body>
</html>
"""


def _format_event(event: Event) -> str:
    timestamp = _format_timestamp(event.timestamp)
    return f"{event.id}  {timestamp}  {event.source:<10} {event.level:<7} {event.message}"


def _format_timestamp(timestamp: datetime) -> str:
    return timestamp.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _first_error(events: list[Event]) -> Event | None:
    for event in events:
        message = event.message.lower()
        if event.level in {"error", "fatal"} or any(
            marker in message for marker in ("error", "fatal", "exception", "timeout", "failed")
        ):
            return event
    return None
