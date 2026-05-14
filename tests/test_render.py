from datetime import UTC, datetime

from traceline.models import Event
from traceline.render import render_html, render_markdown, render_timeline


def test_render_timeline_orders_event_fields() -> None:
    event = Event(
        timestamp=datetime(2026, 5, 13, 14, 3, 2, tzinfo=UTC),
        id="abc123def4567890",
        source="api",
        message="ERROR payment timeout",
        file="app.log",
        line_number=1,
    )

    output = render_timeline([event])

    assert "abc123def4567890  2026-05-13 14:03:02  api" in output
    assert "ERROR payment timeout" in output


def test_render_markdown_escapes_table_pipes() -> None:
    event = Event(
        timestamp=datetime(2026, 5, 13, 14, 3, 2, tzinfo=UTC),
        id="abc123def4567890",
        source="api",
        message="left | right",
        file="app.log",
        line_number=1,
    )

    output = render_markdown([event])

    assert "left \\| right" in output


def test_render_html_includes_incident_summary() -> None:
    event = Event(
        timestamp=datetime(2026, 5, 13, 14, 3, 2, tzinfo=UTC),
        id="abc123def4567890",
        source="api",
        level="error",
        message="ERROR payment timeout",
        file="app.log",
        line_number=1,
    )

    output = render_html([event])

    assert "<strong>Events</strong>1" in output
    assert "<strong>Sources</strong>api: 1" in output
    assert "<strong>First Error</strong>2026-05-13 14:03:02 api: ERROR payment timeout" in output
    assert "Generated locally by TraceLine" in output
