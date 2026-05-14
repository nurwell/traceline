from pathlib import Path

from typer.testing import CliRunner

from traceline.quick import app


def test_tl_analyzes_logs_without_subcommand(tmp_path: Path) -> None:
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
            str(app_log),
            str(edge_log),
            "--tz",
            "Europe/Warsaw",
            "-o",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "Analyzed 2 files: 2 events, 0/2 skipped lines." in result.output
    assert "payment timeout" in result.output
    assert "upstream timed out" in output.read_text(encoding="utf-8")


def test_tl_infers_html_from_output_extension(tmp_path: Path) -> None:
    runner = CliRunner()
    output = tmp_path / "incident.html"
    log_file = tmp_path / "app.log"
    log_file.write_text("2026-05-13T14:03:02Z ERROR payment timeout\n", encoding="utf-8")

    result = runner.invoke(app, [str(log_file), "-o", str(output)])

    assert result.exit_code == 0
    assert "Exported html report" in result.output
    assert "<html" in output.read_text(encoding="utf-8")


def test_tl_accepts_directory_of_logs(tmp_path: Path) -> None:
    runner = CliRunner()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "app.log").write_text(
        "2026-05-13T14:03:02Z ERROR payment timeout\n",
        encoding="utf-8",
    )
    (logs_dir / "edge.txt").write_text(
        '13/May/2026:16:03:04 +0200 "POST /checkout" 504 upstream timed out\n',
        encoding="utf-8",
    )
    (logs_dir / "notes.md").write_text("not a log input\n", encoding="utf-8")

    result = runner.invoke(app, [str(logs_dir), "--tz", "Europe/Warsaw"])

    assert result.exit_code == 0
    assert "Analyzed 2 files: 2 events, 0/2 skipped lines." in result.output
    assert "app" in result.output
    assert "edge" in result.output


def test_tl_rejects_unknown_output_extension(tmp_path: Path) -> None:
    runner = CliRunner()
    log_file = tmp_path / "app.log"
    log_file.write_text("2026-05-13T14:03:02Z ERROR payment timeout\n", encoding="utf-8")

    result = runner.invoke(app, [str(log_file), "-o", str(tmp_path / "incident.report")])

    assert result.exit_code != 0
    assert "Cannot infer report format" in result.output


def test_tl_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "TraceLine" in result.output
