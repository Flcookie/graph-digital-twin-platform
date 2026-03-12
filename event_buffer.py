# event_buffer.py - buffer for out-of-order MQTT events
# time window + bisect insert, output events older than window_ms

import bisect
import datetime
import threading


def parse_time_to_float(time_str: str) -> float:
    """ISO time string -> float for comparison."""
    return datetime.datetime.fromisoformat(time_str).timestamp()


class EventBuffer:
    def __init__(self, window_ms: int = 300, max_size: int | None = None):
        self.window_ms = window_ms
        self._events = []  # (ts, event) sorted by ts
        self._lock = threading.Lock()

    def add(self, event: dict) -> None:
        """Insert event, keep sorted by timestamp."""
        time_str = event.get("time")
        if not time_str:
            return
        ts = parse_time_to_float(time_str)
        item = (ts, event)
        with self._lock:
            bisect.insort(self._events, item)

    def flush_ready(self, now_ts: float | None = None) -> list[dict]:
        """Return events older than window_ms, remove from buffer."""
        if now_ts is None:
            now_ts = datetime.datetime.now().timestamp()
        cutoff = now_ts - (self.window_ms / 1000.0)
        ready = []
        with self._lock:
            while self._events and self._events[0][0] < cutoff:
                _, ev = self._events.pop(0)
                ready.append(ev)
        return ready
