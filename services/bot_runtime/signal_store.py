from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal


SignalSide = Literal["long", "short", "none"]
SignalEvent = Literal["entry", "averaging", "exit"]


@dataclass(frozen=True, slots=True)
class SignalSnapshot:
    side: SignalSide
    ts: datetime
    preset: str
    detail: dict[str, object]


class SignalStore:
    """In-memory latest signals per (symbol, event)."""

    def __init__(self) -> None:
        self._data: dict[tuple[str, SignalEvent], SignalSnapshot] = {}

    def set(self, *, symbol: str, event: SignalEvent, side: SignalSide, preset: str, detail: dict[str, object]) -> None:
        self._data[(symbol, event)] = SignalSnapshot(side=side, ts=datetime.now(tz=timezone.utc), preset=preset, detail=detail)

    def get(self, *, symbol: str, event: SignalEvent) -> SignalSnapshot | None:
        return self._data.get((symbol, event))
