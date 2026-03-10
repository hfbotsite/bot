from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .candle_store import CandleStore
from .indicators import ema


@dataclass(frozen=True, slots=True)
class TfSwitchDecision:
    changed: bool
    active_tf: str
    reason: str | None
    detail: dict[str, object]


class TimeframeSwitcher:
    """Timeframe switching coordinator (MVP).

    - Chain is provided as list of timeframes, first element is base timeframe.
    - Switching happens ONLY when enabled and the bot has an open position.
    - Trigger: EMA200 cross on global timeframe (settings.indicators_tuning.global_timeframe).
        LONG: close crosses EMA200 from above to below => step up
        SHORT: close crosses EMA200 from below to above => step up
    - No cooldown/revert in MVP; when flat => reset to base.
    """

    def __init__(self, *, chain: list[str], ema_length: int = 200):
        if not chain:
            raise ValueError("chain must not be empty")
        self._chain = chain
        self._idx = 0
        self._ema_length = int(ema_length)

    @property
    def chain(self) -> list[str]:
        return list(self._chain)

    @property
    def base_tf(self) -> str:
        return self._chain[0]

    @property
    def active_tf(self) -> str:
        return self._chain[self._idx]

    def reset_to_base(self) -> TfSwitchDecision:
        if self._idx == 0:
            return TfSwitchDecision(changed=False, active_tf=self.active_tf, reason=None, detail={})
        self._idx = 0
        return TfSwitchDecision(changed=True, active_tf=self.active_tf, reason="reset_flat", detail={})

    def step_up(self, *, reason: str, detail: dict[str, object]) -> TfSwitchDecision:
        if self._idx >= len(self._chain) - 1:
            return TfSwitchDecision(changed=False, active_tf=self.active_tf, reason=None, detail=detail)
        self._idx += 1
        return TfSwitchDecision(changed=True, active_tf=self.active_tf, reason=reason, detail=detail)

    def tick_ema200_cross(
        self,
        *,
        store: CandleStore,
        symbol: str,
        global_tf: str,
        has_position: bool,
    ) -> TfSwitchDecision:
        if not has_position:
            return self.reset_to_base()

        candles = store.list(symbol=symbol, timeframe=global_tf)
        closes: list[Decimal] = [c.close for c in candles]
        if len(closes) < self._ema_length + 2:
            return TfSwitchDecision(
                changed=False,
                active_tf=self.active_tf,
                reason=None,
                detail={"warmup": True, "need": self._ema_length + 2, "have": len(closes), "tf": global_tf},
            )

        e = ema(closes, length=self._ema_length)
        if len(e) < 2:
            return TfSwitchDecision(
                changed=False,
                active_tf=self.active_tf,
                reason=None,
                detail={"warmup": True, "tf": global_tf},
            )

        prev_close, last_close = closes[-2], closes[-1]
        prev_ema, last_ema = e[-2], e[-1]

        # LONG cross down OR SHORT cross up => step up (single active_tf for MVP).
        long_cross_down = (prev_close > prev_ema) and (last_close < last_ema)
        short_cross_up = (prev_close < prev_ema) and (last_close > last_ema)

        if not (long_cross_down or short_cross_up):
            return TfSwitchDecision(changed=False, active_tf=self.active_tf, reason=None, detail={})

        reason = "ema200_cross"
        detail = {
            "tf": global_tf,
            "ema_length": self._ema_length,
            "prev_close": str(prev_close),
            "last_close": str(last_close),
            "prev_ema": str(prev_ema),
            "last_ema": str(last_ema),
            "long_cross_down": long_cross_down,
            "short_cross_up": short_cross_up,
            "from_tf": self.active_tf,
        }
        return self.step_up(reason=reason, detail=detail)
