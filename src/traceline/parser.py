from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, tzinfo
from hashlib import sha256
from json import JSONDecodeError, loads
from pathlib import Path
from zoneinfo import ZoneInfo

from traceline.models import Event, Level, ParsedLog, ParseReport, SkippedLine
from traceline.redaction import redact_text

ISO_PREFIX = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"
)
SPACE_UTC_PREFIX = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})(?P<utc>\s+UTC)?"
)
NGINX_PREFIX = re.compile(
    r"^(?P<ts>\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}\s+[+-]\d{4})"
)
APACHE_PREFIX = re.compile(
    r"^\[(?P<ts>\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2}\s+[+-]\d{4})\]"
)
LEVEL_PATTERN = re.compile(r"\b(DEBUG|INFO|WARN|WARNING|ERROR|ERR|FATAL|CRITICAL)\b", re.IGNORECASE)
CONTINUATION_PREFIX = re.compile(
    r"^(\s+|Traceback\b|File \"|Caused by:|\.\.\.|\w+(?:\.\w+)*(?:Error|Exception):)"
)
MAX_SKIPPED_EXAMPLES = 5
MAX_SKIPPED_EXAMPLE_LENGTH = 160

LineParser = Callable[[str, ZoneInfo], tuple[datetime, str, str] | None]


def parse_log_file(path: Path, source: str, timezone_name: str = "UTC") -> list[Event]:
    return parse_log_file_result(path, source, timezone_name=timezone_name).events


def parse_log_file_result(
    path: Path,
    source: str,
    timezone_name: str = "UTC",
    redact: bool = True,
) -> ParsedLog:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return parse_log_lines_result(
            handle,
            source=source,
            file_label=str(path),
            timezone_name=timezone_name,
            redact=redact,
        )


def parse_log_lines_result(
    lines: Iterable[str],
    source: str,
    file_label: str,
    timezone_name: str = "UTC",
    redact: bool = True,
) -> ParsedLog:
    events: list[Event] = []
    timezone = ZoneInfo(timezone_name)
    report = ParseReport()
    pending: tuple[datetime, str, str, int] | None = None

    for line_number, raw_line in enumerate(lines, start=1):
        report.total_lines += 1
        line = raw_line.rstrip("\n")
        parsed = parse_line(line, timezone)
        if parsed is None:
            if pending is not None and _is_continuation_line(line):
                timestamp, message, parser_name, event_line_number = pending
                pending = (timestamp, message + "\n" + line, parser_name, event_line_number)
            else:
                report.skipped_lines += 1
                _record_skipped_example(report, line_number, line)
            continue

        if pending is not None:
            events.append(_build_event(pending, source, file_label, redact))

        timestamp, message, parser_name = parsed
        pending = (timestamp, message, parser_name, line_number)
        report.parsed_lines += 1
        report.parser_counts[parser_name] = report.parser_counts.get(parser_name, 0) + 1

    if pending is not None:
        events.append(_build_event(pending, source, file_label, redact))

    return ParsedLog(events=events, report=report)


def parse_line(line: str, default_timezone: ZoneInfo) -> tuple[datetime, str, str] | None:
    for parser in (_parse_json_line, _parse_regex_line):
        parsed = parser(line, default_timezone)
        if parsed is not None:
            return parsed
    return None


def detect_level(message: str) -> Level:
    match = LEVEL_PATTERN.search(message)
    if match is None:
        if re.search(r"\b5\d\d\b|timeout|failed|exception", message, re.IGNORECASE):
            return Level.error
        return Level.unknown

    value = match.group(1).lower()
    if value == "warn":
        return Level.warning
    if value == "err":
        return Level.error
    if value == "critical":
        return Level.fatal
    return Level(value)


def build_event_id(
    *,
    timestamp: datetime,
    source: str,
    file: Path | str,
    line_number: int,
    message: str,
) -> str:
    raw = f"{timestamp.isoformat()}|{source}|{file}|{line_number}|{message}"
    return sha256(raw.encode("utf-8")).hexdigest()[:16]


def _build_event(
    pending: tuple[datetime, str, str, int],
    source: str,
    file_label: str,
    redact: bool,
) -> Event:
    timestamp, message, parser_name, line_number = pending
    redaction = redact_text(message) if redact else None
    stored_message = redaction.text if redaction else message
    utc_timestamp = timestamp.astimezone(UTC)

    return Event(
        id=build_event_id(
            timestamp=utc_timestamp,
            source=source,
            file=file_label,
            line_number=line_number,
            message=stored_message,
        ),
        timestamp=utc_timestamp,
        source=source,
        message=stored_message,
        file=file_label,
        line_number=line_number,
        level=detect_level(stored_message),
        parser=parser_name,
        redacted=redaction.changed if redaction else False,
    )


def _is_continuation_line(line: str) -> bool:
    return bool(line and CONTINUATION_PREFIX.match(line))


def _record_skipped_example(report: ParseReport, line_number: int, line: str) -> None:
    if len(report.skipped_examples) >= MAX_SKIPPED_EXAMPLES:
        return

    redacted = redact_text(line).text.strip()
    if len(redacted) > MAX_SKIPPED_EXAMPLE_LENGTH:
        redacted = redacted[: MAX_SKIPPED_EXAMPLE_LENGTH - 3] + "..."
    report.skipped_examples.append(SkippedLine(line_number=line_number, text=redacted))


def _parse_regex_line(line: str, default_timezone: ZoneInfo) -> tuple[datetime, str, str] | None:
    for parser_name, pattern, parser in (
        ("iso", ISO_PREFIX, _parse_iso),
        ("space", SPACE_UTC_PREFIX, lambda value: _parse_space_datetime(value, default_timezone)),
        ("nginx", NGINX_PREFIX, _parse_nginx),
        ("apache", APACHE_PREFIX, _parse_nginx),
    ):
        match = pattern.match(line)
        if match is None:
            continue

        raw_timestamp = match.group("ts")
        if parser_name == "space" and match.group("utc"):
            timestamp = _parse_space_datetime(raw_timestamp, UTC)
        else:
            timestamp = parser(raw_timestamp)
        message = line[match.end() :].strip()
        return timestamp, message or line, parser_name

    return None


def _parse_json_line(line: str, default_timezone: ZoneInfo) -> tuple[datetime, str, str] | None:
    try:
        payload = loads(line)
    except JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    timestamp_value = _first_string(payload, ("timestamp", "time", "@timestamp", "ts"))
    if timestamp_value is None:
        return None

    timestamp = _parse_timestamp_value(timestamp_value, default_timezone)
    message = _first_string(payload, ("message", "msg", "log", "event")) or line
    return timestamp, message.strip(), "json"


def _first_string(payload: dict[object, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _parse_timestamp_value(value: str, default_timezone: ZoneInfo) -> datetime:
    if "T" in value:
        return _parse_iso(value)
    return _parse_space_datetime(value.removesuffix(" UTC"), default_timezone)


def _parse_iso(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    timestamp = datetime.fromisoformat(normalized)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp


def _parse_space_datetime(value: str, default_timezone: tzinfo) -> datetime:
    timestamp = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return timestamp.replace(tzinfo=default_timezone)


def _parse_nginx(value: str) -> datetime:
    return datetime.strptime(value, "%d/%b/%Y:%H:%M:%S %z")
