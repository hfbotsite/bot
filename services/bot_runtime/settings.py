from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import json

from services.execution.models import ExchangeId, MarginMode, PositionMode


def _parse_timeframes(raw: str) -> list[str]:
    # Allow either a single timeframe (e.g. "5m") or a comma-separated chain (e.g. "5m, 15m, 1h, 4h").
    tfs = [p.strip().lower() for p in str(raw).split(",")]
    tfs = [tf for tf in tfs if tf]
    if not tfs:
        raise RuntimeError("Timeframes string is empty")
    return tfs


def _first_timeframe(raw: str) -> str:
    return _parse_timeframes(raw)[0]


def _env(name: str, *, required: bool = False, default: str | None = None) -> str | None:
    val = os.environ.get(name, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return val


@dataclass(frozen=True, slots=True)
class ExchangeSecrets:
    api_key: str
    api_secret: str
    api_password: str | None = None


@dataclass(frozen=True, slots=True)
class BotConfig:
    exchange: ExchangeId
    market: str
    base_coin: str
    quote_coin: str

    leverage: int
    margin_mode: MarginMode

    time_sleep: int
    time_sleep_coeff: int
    stop_if_no_balance: bool
    cancel_on_trend: bool
    so_safety_price: Decimal
    new_order_time: int
    emergency_averaging: int
    use_margin: bool
    margin_top: Decimal
    margin_bottom: Decimal
    back_profit: Decimal


@dataclass(frozen=True, slots=True)
class BasicConfig:
    depo: Decimal
    percent_or_amount: bool
    bo_amount: Decimal
    orders_total: int
    active_orders: int


@dataclass(frozen=True, slots=True)
class GridConfig:
    first_step: Decimal
    lift_step: Decimal
    range_cover: int
    first_so_coeff: Decimal
    dynamic_so_coeff: Decimal
    martingale: Decimal


@dataclass(frozen=True, slots=True)
class PresetStochCciConfig:
    use_stoch: bool
    use_cci: bool
    basic_indicator: str  # "stoch" | "cci"
    stoch_short_up_level: Decimal
    stoch_short_low_level: Decimal
    stoch_long_up_level: Decimal
    stoch_long_low_level: Decimal
    cci_short_level: Decimal
    cci_long_level: Decimal
    stoch_fastk_period: int
    stoch_slowk_period: int
    stoch_slowd_period: int
    cci_period: int


@dataclass(frozen=True, slots=True)
class PresetStochRsiConfig:
    use_stoch: bool
    use_rsi: bool
    basic_indicator: str  # "stoch" | "rsi"
    stoch_short_up_level: Decimal
    stoch_short_low_level: Decimal
    stoch_long_up_level: Decimal
    stoch_long_low_level: Decimal
    rsi_short_level: Decimal
    rsi_long_level: Decimal
    stoch_fastk_period: int
    stoch_slowk_period: int
    stoch_slowd_period: int
    rsi_period: int


@dataclass(frozen=True, slots=True)
class PresetCciCrossConfig:
    cci_short_level: Decimal
    cci_long_level: Decimal
    use_price: bool
    cci_period: int


@dataclass(frozen=True, slots=True)
class PresetMaCrossConfig:
    ma1_length: int
    ma2_length: int


@dataclass(frozen=True, slots=True)
class PresetPriceConfig:
    price_delta_short: Decimal
    price_delta_long: Decimal


@dataclass(frozen=True, slots=True)
class PresetRsiSmaRsiCrossConfig:
    rsi_short_up_level: Decimal
    rsi_short_low_level: Decimal
    rsi_long_up_level: Decimal
    rsi_long_low_level: Decimal
    smarsi_length: int
    rsi_period: int


@dataclass(frozen=True, slots=True)
class EntryConfig:
    entry_by_indicators: bool
    entry_use_tv_signals: bool
    entry_use_ema: bool
    entry_use_entry_margin: bool
    entry_margin_top: Decimal
    entry_margin_bottom: Decimal
    entry_timeframe: str
    entry_preset: str

    stoch_cci: PresetStochCciConfig
    stoch_rsi: PresetStochRsiConfig
    cci_cross: PresetCciCrossConfig
    ma_cross: PresetMaCrossConfig
    price: PresetPriceConfig
    rsi_smarsi_cross: PresetRsiSmaRsiCrossConfig


@dataclass(frozen=True, slots=True)
class AveragingConfig:
    enabled: bool
    timeframe: str
    avg_timesleep: int  # seconds
    avg_preset: str

    stoch_cci: PresetStochCciConfig
    stoch_rsi: PresetStochRsiConfig
    cci_cross: PresetCciCrossConfig
    ma_cross: PresetMaCrossConfig
    price: PresetPriceConfig
    rsi_smarsi_cross: PresetRsiSmaRsiCrossConfig


@dataclass(frozen=True, slots=True)
class ExitConfig:
    take_profit: str
    squeeze_profit: Decimal
    trailing_stop: Decimal
    limit_stop: Decimal
    exit_timeframe: str
    exit_use_tv_signals: bool
    exit_profit_level: Decimal
    exit_stop_loss_level: Decimal
    exit_preset: str

    stoch_cci: PresetStochCciConfig
    stoch_rsi: PresetStochRsiConfig
    cci_cross: PresetCciCrossConfig
    ma_cross: PresetMaCrossConfig
    rsi_smarsi_cross: PresetRsiSmaRsiCrossConfig


@dataclass(frozen=True, slots=True)
class IndicatorsTuningConfig:
    global_timeframe: str
    use_stoch_rsi: bool
    use_ema200: bool
    ema200_length: int
    ema200_delta: Decimal
    use_global_stoch: bool

    global_stoch_long_up_level: Decimal
    global_stoch_long_low_level: Decimal
    global_stoch_short_up_level: Decimal
    global_stoch_short_low_level: Decimal

    macd_f: int
    macd_s: int
    macd_signal: int

    bb_period: int
    bb_dev: Decimal

    atr_length: int
    efi_length: int

    extremes_left: int
    extremes_right: int


@dataclass(frozen=True, slots=True)
class TimeframeSwitchingConfig:
    timeframe_switching: bool
    ema_global_switch: bool
    orders_switch: bool
    orders_count: int
    last_candle_switch: bool
    last_candle_count: int
    last_candle_orders: int
    stoch_adjustment: Decimal


@dataclass(frozen=True, slots=True)
class BotSettings:
    bot_id: str
    run_id: str | None

    config_path: Path

    database_url: str

    candles_ws_url: str
    candles_ws_stale_after_seconds: int

    market_data_source: str  # "ws" | "mock"
    mock_speedup: float
    mock_seed: int | None
    mock_start_price: str

    bot: BotConfig
    basic: BasicConfig
    grid: GridConfig
    entry: EntryConfig
    averaging: AveragingConfig
    exit: ExitConfig
    indicators_tuning: IndicatorsTuningConfig
    timeframe_switching: TimeframeSwitchingConfig

    secrets: ExchangeSecrets

    # Execution conventions (v1)
    position_mode: PositionMode

    @property
    def symbol(self) -> str:
        return f"{self.bot.base_coin}/{self.bot.quote_coin}"

    @property
    def working_timeframes(self) -> list[str]:
        tfs: list[str] = []
        tfs.append("1m")
        tfs.append(self.entry.entry_timeframe)
        if self.averaging.enabled:
            tfs.extend(_parse_timeframes(self.averaging.timeframe))
        tfs.append(self.exit.exit_timeframe)
        tfs.append(self.indicators_tuning.global_timeframe)

        # de-dup preserving order
        seen: set[str] = set()
        out: list[str] = []
        for tf in tfs:
            if tf not in seen:
                seen.add(tf)
                out.append(tf)
        return out

    @staticmethod
    def load_from_env() -> "BotSettings":
        config_path = Path(_env("BOT_CONFIG_PATH", required=True) or "")
        if not config_path.exists():
            raise RuntimeError(f"Config file not found: {config_path}")

        with config_path.open("rb") as f:
            raw = json.load(f)

        bot_id = _env("BOT_ID", required=True) or ""
        run_id = _env("RUN_ID", required=False)

        database_url = _env("DATABASE_URL", required=True) or ""

        candles_ws_url = _env("CANDLES_WS_URL", required=False, default="ws://localhost:9999/ws") or ""
        stale = int(_env("CANDLES_WS_STALE_AFTER_SECONDS", default="30") or "30")

        market_data_source = (_env("MARKET_DATA_SOURCE", default="ws") or "ws").lower()
        mock_speedup = float(_env("MOCK_SPEEDUP", default="60") or "60")
        mock_seed_raw = _env("MOCK_SEED", required=False)
        mock_seed = int(mock_seed_raw) if (mock_seed_raw is not None and mock_seed_raw != "") else None
        mock_start_price = _env("MOCK_START_PRICE", default="100.0") or "100.0"

        secrets = ExchangeSecrets(
            api_key=_env("EXCHANGE_API_KEY", required=True) or "",
            api_secret=_env("EXCHANGE_API_SECRET", required=True) or "",
            api_password=_env("EXCHANGE_API_PASSWORD", required=False),
        )

        position_mode = (_env("POSITION_MODE", default="hedge") or "hedge").lower()
        if position_mode not in ("hedge", "one_way"):
            raise RuntimeError("POSITION_MODE must be 'hedge' or 'one_way'")

        # Parse JSON sections
        bot = raw["bot"]
        basic = raw["basic"]
        grid = raw["grid"]
        entry = raw["entry"]
        averaging = raw["averaging"]
        exit_ = raw["exit"]
        ind = raw["indicators_tuning"]
        tf_switch = raw["timeframe_switching"]

        settings = BotSettings(
            bot_id=bot_id,
            run_id=run_id,
            config_path=config_path,
            database_url=database_url,
            candles_ws_url=candles_ws_url,
            candles_ws_stale_after_seconds=stale,
            market_data_source=market_data_source,
            mock_speedup=mock_speedup,
            mock_seed=mock_seed,
            mock_start_price=mock_start_price,
            bot=BotConfig(
                exchange=bot["exchange"],
                market=bot["market"],
                base_coin=bot["base_coin"],
                quote_coin=bot["quote_coin"],
                leverage=int(bot["leverage"]),
                margin_mode=bot["margin_mode"],
                time_sleep=int(bot["time_sleep"]),
                time_sleep_coeff=int(bot["time_sleep_coeff"]),
                stop_if_no_balance=bool(bot["stop_if_no_balance"]),
                cancel_on_trend=bool(bot["cancel_on_trend"]),
                so_safety_price=Decimal(str(bot["so_safety_price"])),
                new_order_time=int(bot["new_order_time"]),
                emergency_averaging=int(bot["emergency_averaging"]),
                use_margin=bool(bot["use_margin"]),
                margin_top=Decimal(str(bot["margin_top"])),
                margin_bottom=Decimal(str(bot["margin_bottom"])),
                back_profit=Decimal(str(bot["back_profit"])),
            ),
            basic=BasicConfig(
                depo=Decimal(str(basic["depo"])),
                percent_or_amount=bool(basic["percent_or_amount"]),
                bo_amount=Decimal(str(basic["bo_amount"])),
                orders_total=int(basic["orders_total"]),
                active_orders=int(basic.get("active_orders", 0)),
            ),
            grid=GridConfig(
                first_step=Decimal(str(grid["first_step"])),
                lift_step=Decimal(str(grid["lift_step"])),
                range_cover=int(grid["range_cover"]),
                first_so_coeff=Decimal(str(grid["first_so_coeff"])),
                dynamic_so_coeff=Decimal(str(grid["dynamic_so_coeff"])),
                martingale=Decimal(str(grid["martingale"])),
            ),
            entry=EntryConfig(
                entry_by_indicators=bool(entry["entry_by_indicators"]),
                entry_use_tv_signals=bool(entry["entry_use_tv_signals"]),
                entry_use_ema=bool(entry["entry_use_ema"]),
                entry_use_entry_margin=bool(entry["entry_use_entry_margin"]),
                entry_margin_top=Decimal(str(entry["entry_margin_top"])),
                entry_margin_bottom=Decimal(str(entry["entry_margin_bottom"])),
                entry_timeframe=str(entry["entry_timeframe"]),
                entry_preset=str(entry["entry_preset"]),
                stoch_cci=PresetStochCciConfig(
                    use_stoch=bool(entry["stoch_cci"]["use_stoch"]),
                    use_cci=bool(entry["stoch_cci"]["use_cci"]),
                    basic_indicator=str(entry["stoch_cci"]["basic_indicator"]),
                    stoch_short_up_level=Decimal(str(entry["stoch_cci"]["stoch_short_up_level"])),
                    stoch_short_low_level=Decimal(str(entry["stoch_cci"]["stoch_short_low_level"])),
                    stoch_long_up_level=Decimal(str(entry["stoch_cci"]["stoch_long_up_level"])),
                    stoch_long_low_level=Decimal(str(entry["stoch_cci"]["stoch_long_low_level"])),
                    cci_short_level=Decimal(str(entry["stoch_cci"]["cci_short_level"])),
                    cci_long_level=Decimal(str(entry["stoch_cci"]["cci_long_level"])),
                    stoch_fastk_period=int(entry["stoch_cci"]["stoch_fastk_period"]),
                    stoch_slowk_period=int(entry["stoch_cci"]["stoch_slowk_period"]),
                    stoch_slowd_period=int(entry["stoch_cci"]["stoch_slowd_period"]),
                    cci_period=int(entry["stoch_cci"]["cci_period"]),
                ),
                stoch_rsi=PresetStochRsiConfig(
                    use_stoch=bool(entry["stoch_rsi"]["use_stoch"]),
                    use_rsi=bool(entry["stoch_rsi"]["use_rsi"]),
                    basic_indicator=str(entry["stoch_rsi"]["basic_indicator"]),
                    stoch_short_up_level=Decimal(str(entry["stoch_rsi"]["stoch_short_up_level"])),
                    stoch_short_low_level=Decimal(str(entry["stoch_rsi"]["stoch_short_low_level"])),
                    stoch_long_up_level=Decimal(str(entry["stoch_rsi"]["stoch_long_up_level"])),
                    stoch_long_low_level=Decimal(str(entry["stoch_rsi"]["stoch_long_low_level"])),
                    rsi_short_level=Decimal(str(entry["stoch_rsi"]["rsi_short_level"])),
                    rsi_long_level=Decimal(str(entry["stoch_rsi"]["rsi_long_level"])),
                    stoch_fastk_period=int(entry["stoch_rsi"]["stoch_fastk_period"]),
                    stoch_slowk_period=int(entry["stoch_rsi"]["stoch_slowk_period"]),
                    stoch_slowd_period=int(entry["stoch_rsi"]["stoch_slowd_period"]),
                    rsi_period=int(entry["stoch_rsi"]["rsi_period"]),
                ),
                cci_cross=PresetCciCrossConfig(
                    cci_short_level=Decimal(str(entry["cci_cross"]["cci_short_level"])),
                    cci_long_level=Decimal(str(entry["cci_cross"]["cci_long_level"])),
                    use_price=bool(entry["cci_cross"]["use_price"]),
                    cci_period=int(entry["cci_cross"]["cci_period"]),
                ),
                ma_cross=PresetMaCrossConfig(
                    ma1_length=int(entry["ma_cross"]["ma1_length"]),
                    ma2_length=int(entry["ma_cross"]["ma2_length"]),
                ),
                price=PresetPriceConfig(
                    price_delta_short=Decimal(str(entry["price"]["price_delta_short"])),
                    price_delta_long=Decimal(str(entry["price"]["price_delta_long"])),
                ),
                rsi_smarsi_cross=PresetRsiSmaRsiCrossConfig(
                    rsi_short_up_level=Decimal(str(entry["rsi_smarsi_cross"]["rsi_short_up_level"])),
                    rsi_short_low_level=Decimal(str(entry["rsi_smarsi_cross"]["rsi_short_low_level"])),
                    rsi_long_up_level=Decimal(str(entry["rsi_smarsi_cross"]["rsi_long_up_level"])),
                    rsi_long_low_level=Decimal(str(entry["rsi_smarsi_cross"]["rsi_long_low_level"])),
                    smarsi_length=int(entry["rsi_smarsi_cross"]["smarsi_length"]),
                    rsi_period=int(entry["rsi_smarsi_cross"]["rsi_period"]),
                ),
            ),
            averaging=AveragingConfig(
                enabled=bool(averaging["enabled"]),
                timeframe=str(averaging["timeframe"]),
                avg_timesleep=int(averaging["avg_timesleep"]),
                avg_preset=str(averaging["avg_preset"]),
                stoch_cci=PresetStochCciConfig(
                    use_stoch=bool(averaging["stoch_cci"]["use_stoch"]),
                    use_cci=bool(averaging["stoch_cci"]["use_cci"]),
                    basic_indicator=str(averaging["stoch_cci"]["basic_indicator"]),
                    stoch_short_up_level=Decimal(str(averaging["stoch_cci"]["stoch_short_up_level"])),
                    stoch_short_low_level=Decimal(str(averaging["stoch_cci"]["stoch_short_low_level"])),
                    stoch_long_up_level=Decimal(str(averaging["stoch_cci"]["stoch_long_up_level"])),
                    stoch_long_low_level=Decimal(str(averaging["stoch_cci"]["stoch_long_low_level"])),
                    cci_short_level=Decimal(str(averaging["stoch_cci"]["cci_short_level"])),
                    cci_long_level=Decimal(str(averaging["stoch_cci"]["cci_long_level"])),
                    stoch_fastk_period=int(averaging["stoch_cci"]["stoch_fastk_period"]),
                    stoch_slowk_period=int(averaging["stoch_cci"]["stoch_slowk_period"]),
                    stoch_slowd_period=int(averaging["stoch_cci"]["stoch_slowd_period"]),
                    cci_period=int(averaging["stoch_cci"]["cci_period"]),
                ),
                stoch_rsi=PresetStochRsiConfig(
                    use_stoch=bool(averaging["stoch_rsi"]["use_stoch"]),
                    use_rsi=bool(averaging["stoch_rsi"]["use_rsi"]),
                    basic_indicator=str(averaging["stoch_rsi"]["basic_indicator"]),
                    stoch_short_up_level=Decimal(str(averaging["stoch_rsi"]["stoch_short_up_level"])),
                    stoch_short_low_level=Decimal(str(averaging["stoch_rsi"]["stoch_short_low_level"])),
                    stoch_long_up_level=Decimal(str(averaging["stoch_rsi"]["stoch_long_up_level"])),
                    stoch_long_low_level=Decimal(str(averaging["stoch_rsi"]["stoch_long_low_level"])),
                    rsi_short_level=Decimal(str(averaging["stoch_rsi"]["rsi_short_level"])),
                    rsi_long_level=Decimal(str(averaging["stoch_rsi"]["rsi_long_level"])),
                    stoch_fastk_period=int(averaging["stoch_rsi"]["stoch_fastk_period"]),
                    stoch_slowk_period=int(averaging["stoch_rsi"]["stoch_slowk_period"]),
                    stoch_slowd_period=int(averaging["stoch_rsi"]["stoch_slowd_period"]),
                    rsi_period=int(averaging["stoch_rsi"]["rsi_period"]),
                ),
                cci_cross=PresetCciCrossConfig(
                    cci_short_level=Decimal(str(averaging["cci_cross"]["cci_short_level"])),
                    cci_long_level=Decimal(str(averaging["cci_cross"]["cci_long_level"])),
                    use_price=bool(averaging["cci_cross"]["use_price"]),
                    cci_period=int(averaging["cci_cross"]["cci_period"]),
                ),
                ma_cross=PresetMaCrossConfig(
                    ma1_length=int(averaging["ma_cross"]["ma1_length"]),
                    ma2_length=int(averaging["ma_cross"]["ma2_length"]),
                ),
                price=PresetPriceConfig(
                    price_delta_short=Decimal(str(averaging["price"]["price_delta_short"])),
                    price_delta_long=Decimal(str(averaging["price"]["price_delta_long"])),
                ),
                rsi_smarsi_cross=PresetRsiSmaRsiCrossConfig(
                    rsi_short_up_level=Decimal(str(averaging["rsi_smarsi_cross"]["rsi_short_up_level"])),
                    rsi_short_low_level=Decimal(str(averaging["rsi_smarsi_cross"]["rsi_short_low_level"])),
                    rsi_long_up_level=Decimal(str(averaging["rsi_smarsi_cross"]["rsi_long_up_level"])),
                    rsi_long_low_level=Decimal(str(averaging["rsi_smarsi_cross"]["rsi_long_low_level"])),
                    smarsi_length=int(averaging["rsi_smarsi_cross"]["smarsi_length"]),
                    rsi_period=int(averaging["rsi_smarsi_cross"]["rsi_period"]),
                ),
            ),
            exit=ExitConfig(
                take_profit=str(exit_["take_profit"]),
                squeeze_profit=Decimal(str(exit_["squeeze_profit"])),
                trailing_stop=Decimal(str(exit_["trailing_stop"])),
                limit_stop=Decimal(str(exit_["limit_stop"])),
                exit_timeframe=str(exit_["exit_timeframe"]),
                exit_use_tv_signals=bool(exit_["exit_use_tv_signals"]),
                exit_profit_level=Decimal(str(exit_["exit_profit_level"])),
                exit_stop_loss_level=Decimal(str(exit_["exit_stop_loss_level"])),
                exit_preset=str(exit_["exit_preset"]),
                stoch_cci=PresetStochCciConfig(
                    use_stoch=bool(exit_["stoch_cci"]["use_stoch"]),
                    use_cci=bool(exit_["stoch_cci"]["use_cci"]),
                    basic_indicator=str(exit_["stoch_cci"]["basic_indicator"]),
                    stoch_short_up_level=Decimal(str(exit_["stoch_cci"]["stoch_short_up_level"])),
                    stoch_short_low_level=Decimal(str(exit_["stoch_cci"]["stoch_short_low_level"])),
                    stoch_long_up_level=Decimal(str(exit_["stoch_cci"]["stoch_long_up_level"])),
                    stoch_long_low_level=Decimal(str(exit_["stoch_cci"]["stoch_long_low_level"])),
                    cci_short_level=Decimal(str(exit_["stoch_cci"]["cci_short_level"])),
                    cci_long_level=Decimal(str(exit_["stoch_cci"]["cci_long_level"])),
                    stoch_fastk_period=int(exit_["stoch_cci"]["stoch_fastk_period"]),
                    stoch_slowk_period=int(exit_["stoch_cci"]["stoch_slowk_period"]),
                    stoch_slowd_period=int(exit_["stoch_cci"]["stoch_slowd_period"]),
                    cci_period=int(exit_["stoch_cci"]["cci_period"]),
                ),
                stoch_rsi=PresetStochRsiConfig(
                    use_stoch=bool(exit_["stoch_rsi"]["use_stoch"]),
                    use_rsi=bool(exit_["stoch_rsi"]["use_rsi"]),
                    basic_indicator=str(exit_["stoch_rsi"]["basic_indicator"]),
                    stoch_short_up_level=Decimal(str(exit_["stoch_rsi"]["stoch_short_up_level"])),
                    stoch_short_low_level=Decimal(str(exit_["stoch_rsi"]["stoch_short_low_level"])),
                    stoch_long_up_level=Decimal(str(exit_["stoch_rsi"]["stoch_long_up_level"])),
                    stoch_long_low_level=Decimal(str(exit_["stoch_rsi"]["stoch_long_low_level"])),
                    rsi_short_level=Decimal(str(exit_["stoch_rsi"]["rsi_short_level"])),
                    rsi_long_level=Decimal(str(exit_["stoch_rsi"]["rsi_long_level"])),
                    stoch_fastk_period=int(exit_["stoch_rsi"]["stoch_fastk_period"]),
                    stoch_slowk_period=int(exit_["stoch_rsi"]["stoch_slowk_period"]),
                    stoch_slowd_period=int(exit_["stoch_rsi"]["stoch_slowd_period"]),
                    rsi_period=int(exit_["stoch_rsi"]["rsi_period"]),
                ),
                cci_cross=PresetCciCrossConfig(
                    cci_short_level=Decimal(str(exit_["cci_cross"]["cci_short_level"])),
                    cci_long_level=Decimal(str(exit_["cci_cross"]["cci_long_level"])),
                    use_price=bool(exit_["cci_cross"]["use_price"]),
                    cci_period=int(exit_["cci_cross"]["cci_period"]),
                ),
                ma_cross=PresetMaCrossConfig(
                    ma1_length=int(exit_["ma_cross"]["ma1_length"]),
                    ma2_length=int(exit_["ma_cross"]["ma2_length"]),
                ),
                rsi_smarsi_cross=PresetRsiSmaRsiCrossConfig(
                    rsi_short_up_level=Decimal(str(exit_["rsi_smarsi_cross"]["rsi_short_up_level"])),
                    rsi_short_low_level=Decimal(str(exit_["rsi_smarsi_cross"]["rsi_short_low_level"])),
                    rsi_long_up_level=Decimal(str(exit_["rsi_smarsi_cross"]["rsi_long_up_level"])),
                    rsi_long_low_level=Decimal(str(exit_["rsi_smarsi_cross"]["rsi_long_low_level"])),
                    smarsi_length=int(exit_["rsi_smarsi_cross"]["smarsi_length"]),
                    rsi_period=int(exit_["rsi_smarsi_cross"]["rsi_period"]),
                ),
            ),
            indicators_tuning=IndicatorsTuningConfig(
                global_timeframe=str(ind["global_timeframe"]),
                use_stoch_rsi=bool(ind["use_stoch_rsi"]),
                use_ema200=bool(ind["use_ema200"]),
                ema200_length=int(ind["ema200_length"]),
                ema200_delta=Decimal(str(ind["ema200_delta"])),
                use_global_stoch=bool(ind["use_global_stoch"]),
                global_stoch_long_up_level=Decimal(str(ind["global_stoch_long_up_level"])),
                global_stoch_long_low_level=Decimal(str(ind["global_stoch_long_low_level"])),
                global_stoch_short_up_level=Decimal(str(ind["global_stoch_short_up_level"])),
                global_stoch_short_low_level=Decimal(str(ind["global_stoch_short_low_level"])),
                macd_f=int(ind["macd_f"]),
                macd_s=int(ind["macd_s"]),
                macd_signal=int(ind["macd_signal"]),
                bb_period=int(ind["bb_period"]),
                bb_dev=Decimal(str(ind["bb_dev"])),
                atr_length=int(ind["atr_length"]),
                efi_length=int(ind["efi_length"]),
                extremes_left=int(ind["extremes_left"]),
                extremes_right=int(ind["extremes_right"]),
            ),
            timeframe_switching=TimeframeSwitchingConfig(
                timeframe_switching=bool(tf_switch["timeframe_switching"]),
                ema_global_switch=bool(tf_switch["ema_global_switch"]),
                orders_switch=bool(tf_switch["orders_switch"]),
                orders_count=int(tf_switch["orders_count"]),
                last_candle_switch=bool(tf_switch["last_candle_switch"]),
                last_candle_count=int(tf_switch["last_candle_count"]),
                last_candle_orders=int(tf_switch["last_candle_orders"]),
                stoch_adjustment=Decimal(str(tf_switch["stoch_adjustment"])),
            ),
            secrets=secrets,
            position_mode=position_mode,  # type: ignore[arg-type]
        )

        _validate_timeframes(settings.working_timeframes)
        return settings


_ALLOWED_TF = {
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "8h",
    "12h",
    "1d",
}


def _validate_timeframes(tfs: Sequence[str]) -> None:
    bad = [tf for tf in tfs if tf not in _ALLOWED_TF]
    if bad:
        raise RuntimeError(f"Unsupported timeframe(s): {bad}. Allowed: {sorted(_ALLOWED_TF)}")
