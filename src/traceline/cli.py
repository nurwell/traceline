from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import typer

from traceline.models import Event
from traceline.parser import parse_log_file_result, parse_log_lines_result
from traceline.redaction import redact_text
from traceline.render import render_csv, render_html, render_json, render_markdown, render_timeline
from traceline.storage import (
    DEFAULT_STORE,
    append_events,
    clear_store,
    get_event,
    init_store,
    load_events,
)

PACKAGE_NAME = "traceline"


def _version_callback(show_version: bool) -> None:
    if not show_version:
        return
    try:
        package_version = version(PACKAGE_NAME)
    except PackageNotFoundError:
        package_version = "0.1.0"
    typer.echo(f"TraceLine {package_version}")
    raise typer.Exit


app = typer.Typer(help="Build incident timelines from local log files.")


class ExportFormat(StrEnum):
    markdown = "markdown"
    json = "json"
    csv = "csv"
    html = "html"


LOG_FILE_SUFFIXES = {".log", ".txt", ".out", ".err", ".json", ".jsonl"}
LOG_PATH_ARGUMENT = typer.Argument(..., exists=True, dir_okay=False, readable=True)
LOG_PATHS_ARGUMENT = typer.Argument(
    ...,
    exists=True,
    dir_okay=True,
    readable=True,
    help="One or more log files or directories to analyze.",
)
OUTPUT_ARGUMENT = typer.Argument(..., dir_okay=False, writable=True)
EVENT_ID_ARGUMENT = typer.Argument(..., help="Event ID printed by timeline/search.")
STORE_OPTION = typer.Option(DEFAULT_STORE, "--store", help="Path to the TraceLine event store.")
SOURCE_OPTION = typer.Option(None, "--source", help="Only include events from this source.")
ADD_SOURCE_OPTION = typer.Option(
    None,
    "--source",
    "-s",
    help="Source label for this log file. Defaults to the filename stem.",
)
ANALYZE_SOURCES_OPTION = typer.Option(
    None,
    "--source",
    "-s",
    help=(
        "Source label. Use once for all files or repeat once per file. "
        "Defaults to each filename stem."
    ),
)
LEVEL_OPTION = typer.Option(None, "--level", help="Only include events with this level.")
SINCE_OPTION = typer.Option(None, "--since", help="Only include events at or after this UTC time.")
UNTIL_OPTION = typer.Option(None, "--until", help="Only include events before this UTC time.")
CONTAINS_OPTION = typer.Option(None, "--contains", help="Only include events containing this text.")
REDACT_OPTION = typer.Option(True, "--redact/--no-redact", help="Redact secrets before storage.")
FORMAT_OPTION = typer.Option(
    None,
    "--format",
    "-f",
    help="Report format. Defaults from output extension.",
)
TIMEZONE_OPTION = typer.Option("UTC", "--timezone", "--tz", help="Timezone for naive timestamps.")
ANALYZE_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    "--out",
    "-o",
    dir_okay=False,
    writable=True,
    help="Optional report path to write.",
)
VERSION_OPTION = typer.Option(
    None,
    "--version",
    callback=_version_callback,
    is_eager=True,
    help="Show the TraceLine version and exit.",
)


@app.callback()
def main(
    version: bool | None = VERSION_OPTION,
) -> None:
    """Build incident timelines from local log files."""


@app.command()
def init(
    store: Path = STORE_OPTION,
) -> None:
    """Create the local TraceLine store if it does not exist."""
    init_store(store)
    typer.echo(f"Initialized TraceLine store at {store}.")


@app.command()
def add(
    path: Path = LOG_PATH_ARGUMENT,
    source: str | None = ADD_SOURCE_OPTION,
    timezone: str = TIMEZONE_OPTION,
    store: Path = STORE_OPTION,
    redact: bool = REDACT_OPTION,
) -> None:
    """Parse a log file and add timestamped events to the local store."""
    source_label = source or path.stem
    try:
        ZoneInfo(timezone)
        parsed = parse_log_file_result(
            path,
            source=source_label,
            timezone_name=timezone,
            redact=redact,
        )
    except ZoneInfoNotFoundError as exc:
        raise typer.BadParameter(f"Unknown timezone: {timezone}") from exc

    append_events(parsed.events, store)
    typer.echo(
        f"Added {len(parsed.events)} events from {path}. "
        f"Skipped {parsed.report.skipped_lines}/{parsed.report.total_lines} lines."
    )
    _suggest_diagnose(path, parsed.report.skipped_lines)


@app.command("from-stdin")
def from_stdin(
    source: str = typer.Option("stdin", "--source", "-s", help="Source label for stdin input."),
    timezone: str = TIMEZONE_OPTION,
    store: Path = STORE_OPTION,
    redact: bool = REDACT_OPTION,
) -> None:
    """Parse log lines from stdin and add timestamped events to the local store."""
    try:
        ZoneInfo(timezone)
        parsed = parse_log_lines_result(
            sys.stdin,
            source=source,
            file_label="<stdin>",
            timezone_name=timezone,
            redact=redact,
        )
    except ZoneInfoNotFoundError as exc:
        raise typer.BadParameter(f"Unknown timezone: {timezone}") from exc

    append_events(parsed.events, store)
    typer.echo(
        f"Added {len(parsed.events)} events from stdin. "
        f"Skipped {parsed.report.skipped_lines}/{parsed.report.total_lines} lines."
    )


@app.command()
def analyze(
    paths: list[Path] = LOG_PATHS_ARGUMENT,
    sources: list[str] | None = ANALYZE_SOURCES_OPTION,
    timezone: str = TIMEZONE_OPTION,
    output: Path | None = ANALYZE_OUTPUT_OPTION,
    format: ExportFormat | None = FORMAT_OPTION,
    redact: bool = REDACT_OPTION,
) -> None:
    """Analyze log files immediately without creating or managing a store."""
    _run_analysis(paths, sources or [], timezone, output, format, redact)


@app.command("run")
def run_files(
    paths: list[Path] = LOG_PATHS_ARGUMENT,
    sources: list[str] | None = ANALYZE_SOURCES_OPTION,
    timezone: str = TIMEZONE_OPTION,
    output: Path | None = ANALYZE_OUTPUT_OPTION,
    format: ExportFormat | None = FORMAT_OPTION,
    redact: bool = REDACT_OPTION,
) -> None:
    """Short alias for analyze."""
    _run_analysis(paths, sources or [], timezone, output, format, redact)


def _run_analysis(
    paths: list[Path],
    sources: list[str],
    timezone: str,
    output: Path | None,
    format: ExportFormat | None,
    redact: bool,
) -> None:
    paths = _expand_input_paths(paths)
    source_labels = _resolve_sources(paths, sources or [])
    output_format = _resolve_format(format, output)

    try:
        ZoneInfo(timezone)
        parsed_logs = [
            parse_log_file_result(path, source=source, timezone_name=timezone, redact=redact)
            for path, source in zip(paths, source_labels, strict=True)
        ]
    except ZoneInfoNotFoundError as exc:
        raise typer.BadParameter(f"Unknown timezone: {timezone}") from exc

    events = sorted(
        (event for parsed in parsed_logs for event in parsed.events),
        key=lambda event: event.timestamp,
    )
    total_lines = sum(parsed.report.total_lines for parsed in parsed_logs)
    skipped_lines = sum(parsed.report.skipped_lines for parsed in parsed_logs)

    typer.echo(
        f"Analyzed {len(paths)} file{'s' if len(paths) != 1 else ''}: "
        f"{len(events)} events, {skipped_lines}/{total_lines} skipped lines."
    )
    _suggest_diagnose(paths[0] if len(paths) == 1 else None, skipped_lines)
    typer.echo(render_timeline(events))

    if output is not None:
        rendered = _render_export(events, output_format)
        output.write_text(rendered, encoding="utf-8")
        typer.echo(f"Exported {output_format} report to {output}.")


@app.command()
def timeline(
    source: str | None = SOURCE_OPTION,
    level: str | None = LEVEL_OPTION,
    since: str | None = SINCE_OPTION,
    until: str | None = UNTIL_OPTION,
    contains: str | None = CONTAINS_OPTION,
    store: Path = STORE_OPTION,
) -> None:
    """Print all captured events ordered by UTC timestamp."""
    events = _filter_events(load_events(store), source, level, since, until, contains)
    typer.echo(render_timeline(events))


@app.command()
def search(
    pattern: str,
    store: Path = STORE_OPTION,
) -> None:
    """Search captured event messages using a regular expression."""
    try:
        expression = re.compile(pattern, flags=re.IGNORECASE)
    except re.error as exc:
        raise typer.BadParameter(f"Invalid regular expression: {exc}") from exc

    events = [event for event in load_events(store) if expression.search(event.message)]
    typer.echo(render_timeline(events))


@app.command("first-error")
def first_error(
    store: Path = STORE_OPTION,
) -> None:
    """Print the first event that looks like an error."""
    expression = re.compile(r"\b(error|fatal|exception|timeout|failed|5\d\d)\b", re.IGNORECASE)
    for event in load_events(store):
        if expression.search(event.message):
            typer.echo(render_timeline([event]))
            return
    typer.echo("No error-like events found.")


@app.command()
def gaps(
    over: int = typer.Option(60, "--over", help="Minimum quiet period in seconds."),
    source: str | None = SOURCE_OPTION,
    store: Path = STORE_OPTION,
) -> None:
    """Print gaps between consecutive events."""
    events = _filter_events(load_events(store), source, None, None, None, None)
    threshold = timedelta(seconds=over)
    lines: list[str] = []

    for previous, current in zip(events, events[1:], strict=False):
        delta = current.timestamp - previous.timestamp
        if delta >= threshold:
            lines.append(
                "Gap: "
                f"{previous.timestamp:%Y-%m-%d %H:%M:%S} -> "
                f"{current.timestamp:%Y-%m-%d %H:%M:%S}, "
                f"{int(delta.total_seconds())} seconds"
            )

    typer.echo("\n".join(lines) if lines else "No gaps found.")


@app.command()
def export(
    output: Path = OUTPUT_ARGUMENT,
    format: ExportFormat | None = FORMAT_OPTION,
    source: str | None = SOURCE_OPTION,
    level: str | None = LEVEL_OPTION,
    since: str | None = SINCE_OPTION,
    until: str | None = UNTIL_OPTION,
    contains: str | None = CONTAINS_OPTION,
    store: Path = STORE_OPTION,
) -> None:
    """Export the current timeline."""
    events = _filter_events(load_events(store), source, level, since, until, contains)
    output_format = _resolve_format(format, output)
    rendered = _render_export(events, output_format)
    output.write_text(rendered, encoding="utf-8")
    typer.echo(f"Exported timeline to {output}.")


@app.command()
def inspect(
    event_id: str = EVENT_ID_ARGUMENT,
    store: Path = STORE_OPTION,
) -> None:
    """Print one event with file and parser metadata."""
    event = get_event(event_id, store)
    if event is None:
        raise typer.BadParameter(f"Unknown event ID: {event_id}")

    typer.echo(render_timeline([event]))
    typer.echo(f"File: {event.file}:{event.line_number}")
    typer.echo(f"Parser: {event.parser}")
    typer.echo(f"Redacted: {event.redacted}")


@app.command()
def sources(
    store: Path = STORE_OPTION,
) -> None:
    """List source labels in the current store."""
    counts: dict[str, int] = {}
    for event in load_events(store):
        counts[event.source] = counts.get(event.source, 0) + 1

    if not counts:
        typer.echo("No sources found.")
        return

    for source, count in sorted(counts.items()):
        typer.echo(f"{source}: {count}")


@app.command()
def stats(
    store: Path = STORE_OPTION,
) -> None:
    """Print event counts by source, level, and parser."""
    events = load_events(store)
    typer.echo(f"Events: {len(events)}")
    _print_counts("Sources", (event.source for event in events))
    _print_counts("Levels", (event.level for event in events))
    _print_counts("Parsers", (event.parser for event in events))


@app.command()
def diagnose(
    path: Path = LOG_PATH_ARGUMENT,
    source: str = typer.Option("diagnose", "--source", "-s"),
    timezone: str = TIMEZONE_OPTION,
) -> None:
    """Parse a file without storing it and report parser coverage."""
    parsed = parse_log_file_result(path, source=source, timezone_name=timezone, redact=False)
    typer.echo(f"Total lines: {parsed.report.total_lines}")
    typer.echo(f"Parsed lines: {parsed.report.parsed_lines}")
    typer.echo(f"Skipped lines: {parsed.report.skipped_lines}")
    for parser_name, count in sorted(parsed.report.parser_counts.items()):
        typer.echo(f"{parser_name}: {count}")
    if parsed.report.skipped_examples:
        typer.echo("Example skipped lines:")
        for skipped in parsed.report.skipped_examples:
            typer.echo(f"  {skipped.line_number}: {skipped.text}")


@app.command()
def redact(
    path: Path = LOG_PATH_ARGUMENT,
) -> None:
    """Print a redacted copy of a file to stdout."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            typer.echo(redact_text(line.rstrip("\n")).text)


@app.command()
def clear(
    yes: bool = typer.Option(False, "--yes", help="Confirm clearing the local store."),
    store: Path = STORE_OPTION,
) -> None:
    """Clear the local TraceLine store."""
    if not yes:
        raise typer.BadParameter("Refusing to clear store without --yes.")
    clear_store(store)
    typer.echo(f"Cleared TraceLine store at {store}.")


def _filter_events(
    events: list[Event],
    source: str | None,
    level: str | None,
    since: str | None,
    until: str | None,
    contains: str | None,
) -> list[Event]:
    since_time = _parse_cli_time(since) if since else None
    until_time = _parse_cli_time(until) if until else None
    contains_lower = contains.lower() if contains else None

    filtered: list[Event] = []
    for event in events:
        if source and event.source != source:
            continue
        if level and event.level != level:
            continue
        if since_time and event.timestamp < since_time:
            continue
        if until_time and event.timestamp >= until_time:
            continue
        if contains_lower and contains_lower not in event.message.lower():
            continue
        filtered.append(event)
    return filtered


def _resolve_sources(paths: list[Path], sources: list[str]) -> list[str]:
    if not sources:
        return [path.stem for path in paths]
    if len(sources) == 1:
        return sources * len(paths)
    if len(sources) == len(paths):
        return sources
    raise typer.BadParameter(
        "Use no --source values, one --source for all files, or one --source per file."
    )


def _expand_input_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(
                sorted(
                    child
                    for child in path.iterdir()
                    if child.is_file() and child.suffix.lower() in LOG_FILE_SUFFIXES
                )
            )
        else:
            expanded.append(path)

    if not expanded:
        raise typer.BadParameter("No supported log files found.")
    return expanded


def _resolve_format(format: ExportFormat | None, output: Path | None) -> ExportFormat:
    if format is not None:
        return format
    if output is None:
        return ExportFormat.markdown

    suffix = output.suffix.lower().lstrip(".")
    if suffix == "md":
        return ExportFormat.markdown
    if suffix in {value.value for value in ExportFormat}:
        return ExportFormat(suffix)
    raise typer.BadParameter(
        f"Cannot infer report format from {output}. Use -f markdown, html, json, or csv."
    )


def _suggest_diagnose(path: Path | None, skipped_lines: int) -> None:
    if skipped_lines <= 0:
        return
    if path is None:
        typer.echo("Some lines were skipped. Run `traceline diagnose FILE` on each input log.")
        return
    typer.echo(
        f"Some lines were skipped. Run `traceline diagnose {path}` "
        "to inspect parser coverage."
    )


def _render_export(events: list[Event], format: ExportFormat) -> str:
    return {
        ExportFormat.markdown: render_markdown,
        ExportFormat.json: render_json,
        ExportFormat.csv: render_csv,
        ExportFormat.html: render_html,
    }[format](events)


def _parse_cli_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    timestamp = datetime.fromisoformat(normalized)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)


def _print_counts(title: str, values: Iterable[object]) -> None:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    typer.echo(title + ":")
    if not counts:
        typer.echo("  none")
        return
    for key, count in sorted(counts.items()):
        typer.echo(f"  {key}: {count}")


if __name__ == "__main__":
    app()
