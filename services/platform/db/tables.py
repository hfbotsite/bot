from __future__ import annotations
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)

from .metadata import metadata


def _uuid_pk() -> Column:
    # SQLAlchemy doesn't ship UUID type for all DBs; we store UUID as text in MVP.
    # In production, prefer sqlalchemy.dialects.postgresql.UUID(as_uuid=True).
    return Column("id", String(36), primary_key=True)


bots = Table(
    "bots",
    metadata,
    _uuid_pk(),
    # Legacy ownership field (kept for backward compatibility in MVP scripts)
    Column("user_id", String(36), nullable=False, index=True),
    # Creator (author) of the bot; will be used later for strategy selection / ownership
    Column("created_by_user_id", String(36), nullable=False, index=True),
    # Human readable name (can be any text, used for UI display)
    Column("name", Text, nullable=False),
    # Unique slug-like name (latin letters/digits/underscore), used as stable identifier
    Column("bot_name", Text, nullable=False),
    Column("exchange", Text, nullable=False),
    Column("market", Text, nullable=False),  # futures
    Column("status", Text, nullable=False, server_default="created"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("bot_name", name="uq_bots_bot_name"),
)

bot_configs = Table(
    "bot_configs",
    metadata,
    _uuid_pk(),
    Column("bot_id", String(36), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("version", Integer, nullable=False),
    Column("config_body", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("bot_id", "version", name="uq_bot_configs_bot_id_version"),
)

bot_runs = Table(
    "bot_runs",
    metadata,
    _uuid_pk(),
    Column("bot_id", String(36), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("config_id", String(36), ForeignKey("bot_configs.id"), nullable=False),
    Column("state", Text, nullable=False),  # starting/running/stopping/stopped/error
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("stopped_at", DateTime(timezone=True), nullable=True),
    Column("nomad_job_id", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

bot_capital_allocation = Table(
    "bot_capital_allocation",
    metadata,
    _uuid_pk(),
    Column("bot_run_id", String(36), ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("asset", Text, nullable=False),
    Column("available_balance", Numeric(38, 18), nullable=False),
    Column("allocation_percent", Numeric(10, 4), nullable=False),
    Column("allocated_balance", Numeric(38, 18), nullable=False),
    Column("ts", DateTime(timezone=True), nullable=False),
)

instruments = Table(
    "instruments",
    metadata,
    _uuid_pk(),
    Column("exchange", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("contract_type", Text, nullable=False),  # linear/inverse
    Column("base_asset", Text, nullable=True),
    Column("quote_asset", Text, nullable=True),
    Column("settle_asset", Text, nullable=True),
    Column("contract_size", Numeric(38, 18), nullable=True),
    Column("lot_size", Numeric(38, 18), nullable=True),
    Column("price_precision", Integer, nullable=True),
    Column("amount_precision", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("exchange", "symbol", name="uq_instruments_exchange_symbol"),
)

orders = Table(
    "orders",
    metadata,
    _uuid_pk(),
    Column("bot_run_id", String(36), ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("exchange", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("exchange_order_id", Text, nullable=True),
    Column("client_order_id", Text, nullable=True),
    Column("type", Text, nullable=True),
    Column("side", Text, nullable=False),  # buy/sell
    Column("position_mode", Text, nullable=True),  # one_way/hedge
    Column("position_side", Text, nullable=True),  # LONG/SHORT/ONE_WAY
    Column("reduce_only", Boolean, nullable=True),
    Column("price", Numeric(38, 18), nullable=True),
    Column("amount", Numeric(38, 18), nullable=True),
    Column("filled", Numeric(38, 18), nullable=True),
    Column("status", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

trade_fills = Table(
    "trade_fills",
    metadata,
    _uuid_pk(),
    Column("bot_run_id", String(36), ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("order_id", String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
    Column("exchange", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("exchange_trade_id", Text, nullable=False),
    Column("ts", DateTime(timezone=True), nullable=False),
    Column("side", Text, nullable=False),
    Column("position_side", Text, nullable=True),
    Column("margin_mode", Text, nullable=True),  # cross/isolated at execution time (if provided by exchange)
    Column("leverage", Numeric(10, 4), nullable=True),  # leverage at execution time (if provided)
    Column("collateral_asset", Text, nullable=True),  # margin/settle asset at execution time
    Column("price", Numeric(38, 18), nullable=False),
    Column("qty", Numeric(38, 18), nullable=False),
    Column("quote_qty", Numeric(38, 18), nullable=True),
    Column("fee_cost", Numeric(38, 18), nullable=True),
    Column("fee_currency", Text, nullable=True),
    Column("is_maker", Boolean, nullable=True),
    UniqueConstraint("exchange", "symbol", "exchange_trade_id", name="uq_trade_fills_exchange_symbol_trade_id"),
)

positions = Table(
    "positions",
    metadata,
    _uuid_pk(),
    Column("bot_run_id", String(36), ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("exchange", Text, nullable=False),
    Column("symbol", Text, nullable=False),
    Column("position_mode", Text, nullable=False),  # one_way/hedge
    Column("position_side", Text, nullable=False),  # ONE_WAY/LONG/SHORT
    Column("status", Text, nullable=False),  # open/closed
    Column("margin_mode", Text, nullable=True),  # cross/isolated (exchange-specific)
    Column("leverage", Numeric(10, 4), nullable=True),  # last known leverage used by bot/exchange
    Column("collateral_asset", Text, nullable=True),  # margin/settle asset used for PnL & margin accounting
    Column("opened_at", DateTime(timezone=True), nullable=True),
    Column("closed_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("bot_run_id", "symbol", "position_mode", "position_side", name="uq_positions_scope"),
)

position_snapshots = Table(
    "position_snapshots",
    metadata,
    _uuid_pk(),
    Column("position_id", String(36), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("ts", DateTime(timezone=True), nullable=False),
    Column("qty", Numeric(38, 18), nullable=False),
    Column("avg_entry_price", Numeric(38, 18), nullable=True),
    Column("mark_price", Numeric(38, 18), nullable=True),
    Column("open_notional", Numeric(38, 18), nullable=True),
    Column("unrealized_pnl_gross", Numeric(38, 18), nullable=True),
    Column("realized_pnl_gross", Numeric(38, 18), nullable=True),
    Column("fees_total", Numeric(38, 18), nullable=True),
    Column("funding_total", Numeric(38, 18), nullable=True),
    Column("margin_mode", Text, nullable=True),
    Column("leverage", Numeric(10, 4), nullable=True),
    Column("initial_margin", Numeric(38, 18), nullable=True),
    Column("maintenance_margin", Numeric(38, 18), nullable=True),
    Column("liquidation_price", Numeric(38, 18), nullable=True),
)

# Lot model (audit) for positions.
# We calculate realized PnL by weighted average in MVP, but keep lots + allocations
# to make PnL explainable and to allow future switch to FIFO/LIFO.
position_lots = Table(
    "position_lots",
    metadata,
    _uuid_pk(),
    Column("position_id", String(36), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("source_fill_id", String(36), ForeignKey("trade_fills.id", ondelete="SET NULL"), nullable=True),
    Column("qty_opened", Numeric(38, 18), nullable=False),
    Column("qty_closed", Numeric(38, 18), nullable=False, server_default="0"),
    Column("entry_price", Numeric(38, 18), nullable=False),
    Column("entry_notional", Numeric(38, 18), nullable=True),
    Column("collateral_asset", Text, nullable=True),
    Column("leverage", Numeric(10, 4), nullable=True),
    Column("meta", JSON, nullable=True),
)

lot_allocations = Table(
    "lot_allocations",
    metadata,
    Column("lot_id", String(36), ForeignKey("position_lots.id", ondelete="CASCADE"), primary_key=True),
    Column("closing_fill_id", String(36), ForeignKey("trade_fills.id", ondelete="CASCADE"), primary_key=True),
    Column("ts", DateTime(timezone=True), nullable=False),
    Column("qty", Numeric(38, 18), nullable=False),
    Column("exit_price", Numeric(38, 18), nullable=True),
    Column("realized_pnl_gross", Numeric(38, 18), nullable=True),
    Column("fee_cost", Numeric(38, 18), nullable=True),
    Column("fee_currency", Text, nullable=True),
    Column("meta", JSON, nullable=True),
)

Index("ix_lot_allocations_closing_fill_id", lot_allocations.c.closing_fill_id)

pnl_ledger_entries = Table(
    "pnl_ledger_entries",
    metadata,
    _uuid_pk(),
    Column("bot_run_id", String(36), ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("position_id", String(36), ForeignKey("positions.id", ondelete="SET NULL"), nullable=True, index=True),
    Column("fill_id", String(36), ForeignKey("trade_fills.id", ondelete="SET NULL"), nullable=True),
    Column("deal_id", String(36), nullable=True),
    Column("ts", DateTime(timezone=True), nullable=False),
    Column("entry_type", Text, nullable=False),  # REALIZED_PNL/FEE/FUNDING/ADJUSTMENT
    Column("currency", Text, nullable=False),
    Column("amount", Numeric(38, 18), nullable=False),
    Column("meta", JSON, nullable=True),
)

deals = Table(
    "deals",
    metadata,
    _uuid_pk(),
    Column("bot_run_id", String(36), ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("position_id", String(36), ForeignKey("positions.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("deal_direction", Text, nullable=False),  # LONG/SHORT
    Column("status", Text, nullable=False),  # open/closed (UI uses only closed)
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=True, index=True),
    Column("exit_reason", Text, nullable=True),  # squeeze_exit/tp_market_exit/stop_loss_exit
    Column("realized_pnl_gross", Numeric(38, 18), nullable=True),
    Column("fees_total", Numeric(38, 18), nullable=True),
    Column("funding_total", Numeric(38, 18), nullable=True),
    Column("realized_pnl_net", Numeric(38, 18), nullable=True),
    Column("entry_avg_price_final", Numeric(38, 18), nullable=True),
    Column("exit_avg_price", Numeric(38, 18), nullable=True),
    Column("max_position_qty", Numeric(38, 18), nullable=True),
    Column("meta", JSON, nullable=True),
)

deal_fills = Table(
    "deal_fills",
    metadata,
    Column("deal_id", String(36), ForeignKey("deals.id", ondelete="CASCADE"), primary_key=True),
    Column("fill_id", String(36), ForeignKey("trade_fills.id", ondelete="CASCADE"), primary_key=True),
    Column("role", Text, nullable=True),  # ENTRY/AVERAGE/EXIT
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

deal_trade_refs = Table(
    "deal_trade_refs",
    metadata,
    Column("deal_id", String(36), ForeignKey("deals.id", ondelete="CASCADE"), primary_key=True),
    Column("exchange", Text, primary_key=True),
    Column("symbol", Text, primary_key=True),
    Column("exchange_trade_id", Text, primary_key=True),
)
