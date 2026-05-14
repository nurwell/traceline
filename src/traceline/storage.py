from __future__ import annotations

import json
from pathlib import Path

from traceline.models import Event

DEFAULT_STORE = Path(".traceline/events.jsonl")


def append_events(events: list[Event], store: Path = DEFAULT_STORE) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(event.model_dump_json() + "\n")


def init_store(store: Path = DEFAULT_STORE) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    store.touch(exist_ok=True)


def clear_store(store: Path = DEFAULT_STORE) -> None:
    if store.exists():
        store.unlink()
    store.parent.mkdir(parents=True, exist_ok=True)


def load_events(store: Path = DEFAULT_STORE) -> list[Event]:
    if not store.exists():
        return []

    events: list[Event] = []
    with store.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            events.append(Event.model_validate(json.loads(line)))

    return sorted(events, key=lambda event: event.timestamp)


def get_event(event_id: str, store: Path = DEFAULT_STORE) -> Event | None:
    for event in load_events(store):
        if event.id == event_id:
            return event
    return None
