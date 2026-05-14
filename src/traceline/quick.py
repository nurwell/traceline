from __future__ import annotations

from pathlib import Path

import typer

from traceline.cli import (
    ANALYZE_OUTPUT_OPTION,
    ANALYZE_SOURCES_OPTION,
    FORMAT_OPTION,
    LOG_PATHS_ARGUMENT,
    REDACT_OPTION,
    TIMEZONE_OPTION,
    VERSION_OPTION,
    ExportFormat,
    _run_analysis,
)

app = typer.Typer(
    help="Turn local log files into an incident timeline.",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def main(
    paths: list[Path] = LOG_PATHS_ARGUMENT,
    sources: list[str] | None = ANALYZE_SOURCES_OPTION,
    timezone: str = TIMEZONE_OPTION,
    output: Path | None = ANALYZE_OUTPUT_OPTION,
    format: ExportFormat | None = FORMAT_OPTION,
    redact: bool = REDACT_OPTION,
    version: bool | None = VERSION_OPTION,
) -> None:
    """Analyze log files."""
    _run_analysis(paths, sources or [], timezone, output, format, redact)
