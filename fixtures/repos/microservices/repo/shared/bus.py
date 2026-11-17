"""The event bus the three services talk through.

In production the bus is the platform team's broker client (`comptoir_broker`, not in
this repository). The broker delivers every event *at least once*: after a consumer
restart or a lost acknowledgement the same event comes again, with the same `id`.
See docs/adr/0002-at-least-once-delivery.md.

`InMemoryBus` is what tests and local runs use. It delivers every event twice, on
purpose: a consumer that is not idempotent fails its own tests.
"""
from __future__ import annotations

import copy
import os
from typing import Any, Callable, Protocol

Event = dict[str, Any]
Handler = Callable[[Event], None]


class Bus(Protocol):
    def subscribe(self, event_type: str, handler: Handler) -> None: ...

    def publish(self, event: Event) -> None: ...


def envelope(event_type: str, event_id: str, occurred_at: str, payload: dict[str, Any]) -> Event:
    """The envelope every event travels in. `event_id` stays the same when the same
    fact is published again: consumers use it to recognise a redelivery."""
    return {"id": event_id, "type": event_type, "occurred_at": occurred_at, "payload": payload}


class InMemoryBus:
    """Synchronous bus for tests and local runs. `deliveries` is how many times each
    subscriber receives each event; only the tests of the bus itself lower it to 1."""

    def __init__(self, deliveries: int = 2) -> None:
        if deliveries < 1:
            raise ValueError("deliveries must be at least 1")
        self.deliveries = deliveries
        self._handlers: dict[str, list[Handler]] = {}
        self._published: list[Event] = []

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: Event) -> None:
        self._published.append(copy.deepcopy(event))
        for _ in range(self.deliveries):
            for handler in list(self._handlers.get(event["type"], [])):
                handler(copy.deepcopy(event))  # each delivery is its own copy, as over a network

    def published(self, event_type: str | None = None) -> list[Event]:
        """The events published so far, once each, oldest first."""
        return [copy.deepcopy(e) for e in self._published if event_type in (None, e["type"])]


def connect() -> Bus:
    """The bus of the running process: the broker when BROKER_URL is set, memory otherwise."""
    url = os.environ.get("BROKER_URL", "")
    if not url:
        return InMemoryBus()
    from comptoir_broker import connect as connect_broker  # shipped in the base image, not in this repository

    return connect_broker(url)
