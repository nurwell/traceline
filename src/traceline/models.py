from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Level(StrEnum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    fatal = "fatal"
    unknown = "unknown"


class Event(BaseModel):
    id: str = Field(min_length=12)
    timestamp: datetime
    source: str = Field(min_length=1)
    message: str = Field(min_length=1)
    file: str
    line_number: int = Field(ge=1)
    level: Level = Level.unknown
    parser: str = "unknown"
    redacted: bool = False


class SkippedLine(BaseModel):
    line_number: int = Field(ge=1)
    text: str


class ParseReport(BaseModel):
    total_lines: int = 0
    parsed_lines: int = 0
    skipped_lines: int = 0
    parser_counts: dict[str, int] = Field(default_factory=dict)
    skipped_examples: list[SkippedLine] = Field(default_factory=list)


class ParsedLog(BaseModel):
    events: list[Event]
    report: ParseReport
