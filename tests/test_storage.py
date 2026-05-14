from datetime import UTC, datetime
from pathlib import Path

from traceline.models import Event
from traceline.storage import append_events, clear_store, get_event, init_store, load_events


def test_storage_roundtrip_and_lookup(tmp_path: Path) -> None:
    store = tmp_path / "events.jsonl"
    event = Event(
        id="abc123def4567890",
        timestamp=datetime(2026, 5, 13, 14, 3, 2, tzinfo=UTC),
        source="api",
        message="ERROR payment timeout",
        file="app.log",
        line_number=1,
    )

    init_store(store)
    append_events([event], store)

    assert load_events(store) == [event]
    assert get_event("abc123def4567890", store) == event

    clear_store(store)

    assert load_events(store) == []
