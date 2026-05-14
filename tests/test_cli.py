import re
from pathlib import Path

from typer.testing import CliRunner

from traceline.cli import app

ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def clean_output(output: str) -> str:
    return ANSI_PATTERN.sub("", output)


def test_cli_ingests_and_exports_json(tmp_path: Path) -> None:
    runner = CliRunner()
    store = tmp_path / "events.jsonl"
    output = tmp_path / "timeline.json"
    log_file = tmp_path / "app.log"
    log_file.write_text("2026-05-13T14:03:02Z ERROR payment timeout\n", encoding="utf-8")

    add_result = runner.invoke(
        app,
        ["add", str(log_file), "--source", "api", "--store", str(store)],
    )
    export_result = runner.invoke(
        app,
        ["export", str(output), "--format", "json", "--store", str(store)],
    )

    assert add_result.exit_code == 0
    assert "Added 1 events" in add_result.output
    assert export_result.exit_code == 0
    assert "payment timeout" in output.read_text(encoding="utf-8")


def test_cli_add_defaults_source_to_file_stem(tmp_path: Path) -> None:
    runner = CliRunner()
    store = tmp_path / "events.jsonl"
    log_file = tmp_path / "worker.log"
    log_file.write_text("2026-05-13T14:03:02Z ERROR job failed\n", encoding="utf-8")

    add_result = runner.invoke(app, ["add", str(log_file), "--store", str(store)])
    timeline_result = runner.invoke(app, ["timeline", "--store", str(store)])

    assert add_result.exit_code == 0
    assert timeline_result.exit_code == 0
    assert "worker" in timeline_result.output
    assert "ERROR job failed" in timeline_result.output


def test_cli_clear_requires_confirmation(tmp_path: Path) -> None:
    runner = CliRunner()
    store = tmp_path / "events.jsonl"

    result = runner.invoke(app, ["clear", "--store", str(store)])

    assert result.exit_code != 0
    assert "without --yes" in clean_output(result.output)


def test_cli_ingests_from_stdin(tmp_path: Path) -> None:
    runner = CliRunner()
    store = tmp_path / "events.jsonl"

    result = runner.invoke(
        app,
        ["from-stdin", "--source", "pipe", "--store", str(store)],
        input="2026-05-13T14:03:02Z ERROR payment timeout\nbad line\n",
    )
    timeline_result = runner.invoke(app, ["timeline", "--store", str(store)])

    assert result.exit_code == 0
    assert "Added 1 events from stdin. Skipped 1/2 lines." in result.output
    assert timeline_result.exit_code == 0
    assert "pipe" in timeline_result.output
    assert "ERROR payment timeout" in timeline_result.output


def test_cli_from_stdin_defaults_source_to_stdin(tmp_path: Path) -> None:
    runner = CliRunner()
    store = tmp_path / "events.jsonl"

    result = runner.invoke(
        app,
        ["from-stdin", "--store", str(store)],
        input="2026-05-13T14:03:02Z ERROR payment timeout\n",
    )
    timeline_result = runner.invoke(app, ["timeline", "--store", str(store)])

    assert result.exit_code == 0
    assert timeline_result.exit_code == 0
    assert "stdin" in timeline_result.output


def test_cli_analyze_prints_timeline_and_exports_without_store(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "incident.md"
    app_log = tmp_path / "app.log"
    edge_log = tmp_path / "edge.log"
    app_log.write_text("2026-05-13T14:03:02Z ERROR payment timeout\n", encoding="utf-8")
    edge_log.write_text(
        '13/May/2026:16:03:04 +0200 "POST /checkout" 504 upstream timed out\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "analyze",
            str(app_log),
            str(edge_log),
            "--timezone",
            "Europe/Warsaw",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "Analyzed 2 files: 2 events, 0/2 skipped lines." in result.output
    assert "app" in result.output
    assert "edge" in result.output
    assert "payment timeout" in output.read_text(encoding="utf-8")


def test_cli_run_is_short_alias_for_analyze(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "incident.html"
    app_log = tmp_path / "app.log"
    edge_log = tmp_path / "edge.log"
    app_log.write_text("2026-05-13 14:03:02 UTC ERROR payment timeout\n", encoding="utf-8")
    edge_log.write_text(
        '13/May/2026:16:03:04 +0200 "POST /checkout" 504 upstream timed out\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "run",
            str(app_log),
            str(edge_log),
            "--tz",
            "Europe/Warsaw",
            "--out",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "Analyzed 2 files: 2 events, 0/2 skipped lines." in result.output
    assert "2026-05-13 14:03:02" in result.output
    assert "Exported html report" in result.output
    assert "<html" in output.read_text(encoding="utf-8")


def test_cli_analyze_rejects_mismatched_sources(tmp_path: Path) -> None:
    runner = CliRunner()
    app_log = tmp_path / "app.log"
    edge_log = tmp_path / "edge.log"
    deploy_log = tmp_path / "deploy.log"
    for log_file in (app_log, edge_log, deploy_log):
        log_file.write_text("2026-05-13T14:03:02Z INFO event\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "analyze",
            "--source",
            "app",
            "--source",
            "edge",
            str(app_log),
            str(edge_log),
            str(deploy_log),
        ],
    )

    assert result.exit_code != 0
    assert "--source per file" in clean_output(result.output)


def test_cli_add_suggests_diagnose_when_lines_are_skipped(tmp_path: Path) -> None:
    runner = CliRunner()
    store = tmp_path / "events.jsonl"
    log_file = tmp_path / "app.log"
    log_file.write_text(
        "2026-05-13T14:03:02Z ERROR payment timeout\nunparsed line\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["add", str(log_file), "--store", str(store)])

    assert result.exit_code == 0
    assert "Skipped 1/2 lines" in result.output
    assert f"traceline diagnose {log_file}" in result.output


def test_cli_diagnose_shows_redacted_skipped_examples(tmp_path: Path) -> None:
    runner = CliRunner()
    log_file = tmp_path / "app.log"
    log_file.write_text(
        "2026-05-13T14:03:02Z ERROR payment timeout\noperator note token=secret123\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["diagnose", str(log_file)])

    assert result.exit_code == 0
    assert "Example skipped lines:" in result.output
    assert "2: operator note token=[REDACTED]" in result.output


def test_cli_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "TraceLine" in result.output
