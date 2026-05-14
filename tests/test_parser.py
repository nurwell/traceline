from datetime import UTC
from pathlib import Path

from traceline.models import Level
from traceline.parser import parse_log_file, parse_log_file_result, parse_log_lines_result


def test_parse_multiple_timestamp_formats(tmp_path: Path) -> None:
    log_file = tmp_path / "mixed.log"
    log_file.write_text(
        "\n".join(
            [
                "2026-05-13T14:03:02Z ERROR payment timeout",
                "2026-05-13 14:04:30 UTC rollback started",
                '13/May/2026:16:03:04 +0200 "POST /checkout" 504 upstream timed out',
                "line without timestamp",
            ]
        ),
        encoding="utf-8",
    )

    events = parse_log_file(log_file, source="test")

    assert len(events) == 3
    assert events[0].timestamp.tzinfo == UTC
    assert events[0].id
    assert events[0].level == Level.error
    assert events[0].message == "ERROR payment timeout"
    assert events[1].message == "rollback started"
    assert events[2].message == '"POST /checkout" 504 upstream timed out'


def test_parse_naive_timestamp_with_supplied_timezone(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text("2026-05-13 16:03:04 payment timeout\n", encoding="utf-8")

    events = parse_log_file(log_file, source="app", timezone_name="Europe/Warsaw")

    assert len(events) == 1
    assert events[0].timestamp.hour == 14


def test_parse_space_timestamp_with_utc_suffix_ignores_supplied_timezone(tmp_path: Path) -> None:
    log_file = tmp_path / "deploy.log"
    log_file.write_text("2026-05-13 16:03:04 UTC deploy started\n", encoding="utf-8")

    events = parse_log_file(log_file, source="deploy", timezone_name="Europe/Warsaw")

    assert len(events) == 1
    assert events[0].timestamp.hour == 16


def test_parse_json_log_and_report_counts(tmp_path: Path) -> None:
    log_file = tmp_path / "json.log"
    log_file.write_text(
        '{"time":"2026-05-13T14:03:02Z","level":"error","message":"failed checkout"}\n'
        "bad line\n",
        encoding="utf-8",
    )

    parsed = parse_log_file_result(log_file, source="json")

    assert parsed.report.total_lines == 2
    assert parsed.report.parsed_lines == 1
    assert parsed.report.skipped_lines == 1
    assert parsed.report.skipped_examples[0].line_number == 2
    assert parsed.report.skipped_examples[0].text == "bad line"
    assert parsed.report.parser_counts == {"json": 1}
    assert parsed.events[0].parser == "json"
    assert parsed.events[0].message == "failed checkout"


def test_parse_redacts_secrets_by_default(tmp_path: Path) -> None:
    log_file = tmp_path / "secret.log"
    log_file.write_text(
        "2026-05-13T14:03:02Z Authorization: Bearer sk_live_abc123\n",
        encoding="utf-8",
    )

    events = parse_log_file(log_file, source="api")

    assert events[0].message == "Authorization: Bearer [REDACTED]"
    assert events[0].redacted is True


def test_parse_log_lines_uses_supplied_file_label() -> None:
    parsed = parse_log_lines_result(
        ["2026-05-13T14:03:02Z ERROR payment timeout\n"],
        source="stdin",
        file_label="<stdin>",
    )

    assert len(parsed.events) == 1
    assert parsed.events[0].file == "<stdin>"
    assert parsed.events[0].line_number == 1
    assert parsed.events[0].message == "ERROR payment timeout"


def test_parse_joins_stack_trace_continuation_lines() -> None:
    parsed = parse_log_lines_result(
        [
            "2026-05-13T14:03:02Z ERROR checkout failed\n",
            "Traceback (most recent call last):\n",
            '  File "checkout.py", line 12, in pay\n',
            "TimeoutError: upstream timeout\n",
            "2026-05-13T14:03:05Z INFO recovered\n",
        ],
        source="app",
        file_label="app.log",
    )

    assert len(parsed.events) == 2
    assert parsed.report.total_lines == 5
    assert parsed.report.parsed_lines == 2
    assert parsed.report.skipped_lines == 0
    assert parsed.events[0].line_number == 1
    assert parsed.events[0].message == (
        "ERROR checkout failed\n"
        "Traceback (most recent call last):\n"
        '  File "checkout.py", line 12, in pay\n'
        "TimeoutError: upstream timeout"
    )
    assert parsed.events[1].message == "INFO recovered"


def test_parse_does_not_join_unrelated_unparsed_lines() -> None:
    parsed = parse_log_lines_result(
        [
            "2026-05-13T14:03:02Z INFO deploy started\n",
            "unstructured operator note\n",
        ],
        source="deploy",
        file_label="deploy.log",
    )

    assert len(parsed.events) == 1
    assert parsed.report.skipped_lines == 1
    assert parsed.events[0].message == "INFO deploy started"


def test_parse_redacts_skipped_line_examples() -> None:
    parsed = parse_log_lines_result(
        [
            "2026-05-13T14:03:02Z INFO deploy started\n",
            "operator note token=secret123\n",
        ],
        source="deploy",
        file_label="deploy.log",
    )

    assert parsed.report.skipped_examples[0].text == "operator note token=[REDACTED]"
