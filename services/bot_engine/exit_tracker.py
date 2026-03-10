from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


ExitReason = Literal["squeeze_exit", "tp_market_exit", "stop_loss_exit", "indicators_exit"]


@dataclass(frozen=True, slots=True)
class ExitIntent:
    """Tracks an intended exit reason until the position is actually closed (qty -> 0 by fills)."""

    position_id: str
    bot_run_id: str
    symbol: str
    position_side: str  # LONG/SHORT/ONE_WAY
    reason: ExitReason
    ts: datetime


class ExitTracker:
    def __init__(self) -> None:
        self._by_position_id: dict[str, ExitIntent] = {}

    def set_exit_intent(self, intent: ExitIntent) -> None:
        self._by_position_id[intent.position_id] = intent

    def get_exit_intent(self, position_id: str) -> Optional[ExitIntent]:
        return self._by_position_id.get(position_id)

    def clear_exit_intent(self, position_id: str) -> None:
        self._by_position_id.pop(position_id, None)
