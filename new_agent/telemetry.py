from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict


@dataclass
class TelemetryEvent:
    name: str
    timestamp: float
    metadata: Dict[str, object]


class TelemetryStore:
    def __init__(self) -> None:
        self.counters = defaultdict(int)
        self.timings = defaultdict(list)
        self.last_event: TelemetryEvent | None = None

    def record(self, name: str, metadata: Dict[str, object] | None = None) -> None:
        self.counters[name] += 1
        self.last_event = TelemetryEvent(name=name, timestamp=time.time(), metadata=metadata or {})

    def record_timing(self, name: str, ms: float) -> None:
        self.timings[name].append(ms)

    def snapshot(self) -> Dict[str, object]:
        avg_timings = {}
        for key, values in self.timings.items():
            if values:
                avg_timings[key] = sum(values) / len(values)
        return {
            "counters": dict(self.counters),
            "avg_timings_ms": avg_timings,
            "last_event": None if not self.last_event else {
                "name": self.last_event.name,
                "timestamp": self.last_event.timestamp,
                "metadata": self.last_event.metadata,
            },
        }


TELEMETRY = TelemetryStore()
