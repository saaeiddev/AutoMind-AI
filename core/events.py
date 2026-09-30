from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Any, Callable


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event: str, handler: Callable[[Any], None]) -> Callable[[], None]:
        with self._lock:
            self._handlers[event].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._handlers[event]:
                    self._handlers[event].remove(handler)

        return unsubscribe

    def publish(self, event: str, payload: Any = None) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event, ()))
        for handler in handlers:
            handler(payload)
