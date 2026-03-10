"""baseline_v1

Revision ID: d1ea1ce7bcfd
Revises:
Create Date: 2026-03-07 22:38:12.810673

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d1ea1ce7bcfd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Platform baseline schema (v1)

    op.create_table(
        "bots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("market", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="created"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bots_user_id", "bots", ["user_id"], unique=False)

    op.create_table(
        "bot_configs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bot_id", sa.String(length=36), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("config_body", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("bot_id", "version", name="uq_bot_configs_bot_id_version"),
    )
    op.create_index("ix_bot_configs_bot_id", "bot_configs", ["bot_id"], unique=False)

    op.create_table(
        "bot_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bot_id", sa.String(length=36), sa.ForeignKey("bots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("config_id", sa.String(length=36), sa.ForeignKey("bot_configs.id"), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nomad_job_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bot_runs_bot_id", "bot_runs", ["bot_id"], unique=False)

    op.create_table(
        "bot_capital_allocation",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bot_run_id", sa.String(length=36), sa.ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset", sa.Text(), nullable=False),
        sa.Column("available_balance", sa.Numeric(38, 18), nullable=False),
        sa.Column("allocation_percent", sa.Numeric(10, 4), nullable=False),
        sa.Column("allocated_balance", sa.Numeric(38, 18), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bot_capital_allocation_bot_run_id", "bot_capital_allocation", ["bot_run_id"], unique=False)

    op.create_table(
        "instruments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("contract_type", sa.Text(), nullable=False),
        sa.Column("base_asset", sa.Text(), nullable=True),
        sa.Column("quote_asset", sa.Text(), nullable=True),
        sa.Column("settle_asset", sa.Text(), nullable=True),
        sa.Column("contract_size", sa.Numeric(38, 18), nullable=True),
        sa.Column("lot_size", sa.Numeric(38, 18), nullable=True),
        sa.Column("price_precision", sa.Integer(), nullable=True),
        sa.Column("amount_precision", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("exchange", "symbol", name="uq_instruments_exchange_symbol"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bot_run_id", sa.String(length=36), sa.ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("exchange_order_id", sa.Text(), nullable=True),
        sa.Column("client_order_id", sa.Text(), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("position_mode", sa.Text(), nullable=True),
        sa.Column("position_side", sa.Text(), nullable=True),
        sa.Column("reduce_only", sa.Boolean(), nullable=True),
        sa.Column("price", sa.Numeric(38, 18), nullable=True),
        sa.Column("amount", sa.Numeric(38, 18), nullable=True),
        sa.Column("filled", sa.Numeric(38, 18), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_orders_bot_run_id", "orders", ["bot_run_id"], unique=False)

    op.create_table(
        "trade_fills",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bot_run_id", sa.String(length=36), sa.ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.String(length=36), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("exchange_trade_id", sa.Text(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("position_side", sa.Text(), nullable=True),
        sa.Column("margin_mode", sa.Text(), nullable=True),
        sa.Column("leverage", sa.Numeric(10, 4), nullable=True),
        sa.Column("collateral_asset", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(38, 18), nullable=False),
        sa.Column("qty", sa.Numeric(38, 18), nullable=False),
        sa.Column("quote_qty", sa.Numeric(38, 18), nullable=True),
        sa.Column("fee_cost", sa.Numeric(38, 18), nullable=True),
        sa.Column("fee_currency", sa.Text(), nullable=True),
        sa.Column("is_maker", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("exchange", "symbol", "exchange_trade_id", name="uq_trade_fills_exchange_symbol_trade_id"),
    )
    op.create_index("ix_trade_fills_bot_run_id", "trade_fills", ["bot_run_id"], unique=False)

    op.create_table(
        "positions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bot_run_id", sa.String(length=36), sa.ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("position_mode", sa.Text(), nullable=False),
        sa.Column("position_side", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("margin_mode", sa.Text(), nullable=True),
        sa.Column("leverage", sa.Numeric(10, 4), nullable=True),
        sa.Column("collateral_asset", sa.Text(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("bot_run_id", "symbol", "position_mode", "position_side", name="uq_positions_scope"),
    )
    op.create_index("ix_positions_bot_run_id", "positions", ["bot_run_id"], unique=False)

    op.create_table(
        "position_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("position_id", sa.String(length=36), sa.ForeignKey("positions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("qty", sa.Numeric(38, 18), nullable=False),
        sa.Column("avg_entry_price", sa.Numeric(38, 18), nullable=True),
        sa.Column("mark_price", sa.Numeric(38, 18), nullable=True),
        sa.Column("open_notional", sa.Numeric(38, 18), nullable=True),
        sa.Column("unrealized_pnl_gross", sa.Numeric(38, 18), nullable=True),
        sa.Column("realized_pnl_gross", sa.Numeric(38, 18), nullable=True),
        sa.Column("fees_total", sa.Numeric(38, 18), nullable=True),
        sa.Column("funding_total", sa.Numeric(38, 18), nullable=True),
        sa.Column("margin_mode", sa.Text(), nullable=True),
        sa.Column("leverage", sa.Numeric(10, 4), nullable=True),
        sa.Column("initial_margin", sa.Numeric(38, 18), nullable=True),
        sa.Column("maintenance_margin", sa.Numeric(38, 18), nullable=True),
        sa.Column("liquidation_price", sa.Numeric(38, 18), nullable=True),
    )
    op.create_index("ix_position_snapshots_position_id", "position_snapshots", ["position_id"], unique=False)

    op.create_table(
        "position_lots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("position_id", sa.String(length=36), sa.ForeignKey("positions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_fill_id", sa.String(length=36), sa.ForeignKey("trade_fills.id", ondelete="SET NULL"), nullable=True),
        sa.Column("qty_opened", sa.Numeric(38, 18), nullable=False),
        sa.Column("qty_closed", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("entry_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("entry_notional", sa.Numeric(38, 18), nullable=True),
        sa.Column("collateral_asset", sa.Text(), nullable=True),
        sa.Column("leverage", sa.Numeric(10, 4), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_position_lots_position_id", "position_lots", ["position_id"], unique=False)

    op.create_table(
        "lot_allocations",
        sa.Column("lot_id", sa.String(length=36), sa.ForeignKey("position_lots.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "closing_fill_id",
            sa.String(length=36),
            sa.ForeignKey("trade_fills.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("qty", sa.Numeric(38, 18), nullable=False),
        sa.Column("exit_price", sa.Numeric(38, 18), nullable=True),
        sa.Column("realized_pnl_gross", sa.Numeric(38, 18), nullable=True),
        sa.Column("fee_cost", sa.Numeric(38, 18), nullable=True),
        sa.Column("fee_currency", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_lot_allocations_closing_fill_id", "lot_allocations", ["closing_fill_id"], unique=False)

    op.create_table(
        "pnl_ledger_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bot_run_id", sa.String(length=36), sa.ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position_id", sa.String(length=36), sa.ForeignKey("positions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fill_id", sa.String(length=36), sa.ForeignKey("trade_fills.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deal_id", sa.String(length=36), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_pnl_ledger_entries_bot_run_id", "pnl_ledger_entries", ["bot_run_id"], unique=False)
    op.create_index("ix_pnl_ledger_entries_position_id", "pnl_ledger_entries", ["position_id"], unique=False)

    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("bot_run_id", sa.String(length=36), sa.ForeignKey("bot_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position_id", sa.String(length=36), sa.ForeignKey("positions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("deal_direction", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("realized_pnl_gross", sa.Numeric(38, 18), nullable=True),
        sa.Column("fees_total", sa.Numeric(38, 18), nullable=True),
        sa.Column("funding_total", sa.Numeric(38, 18), nullable=True),
        sa.Column("realized_pnl_net", sa.Numeric(38, 18), nullable=True),
        sa.Column("entry_avg_price_final", sa.Numeric(38, 18), nullable=True),
        sa.Column("exit_avg_price", sa.Numeric(38, 18), nullable=True),
        sa.Column("max_position_qty", sa.Numeric(38, 18), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_deals_bot_run_id", "deals", ["bot_run_id"], unique=False)
    op.create_index("ix_deals_position_id", "deals", ["position_id"], unique=False)
    op.create_index("ix_deals_closed_at", "deals", ["closed_at"], unique=False)

    op.create_table(
        "deal_fills",
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("fill_id", sa.String(length=36), sa.ForeignKey("trade_fills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "deal_trade_refs",
        sa.Column("deal_id", sa.String(length=36), sa.ForeignKey("deals.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("exchange", sa.Text(), primary_key=True),
        sa.Column("symbol", sa.Text(), primary_key=True),
        sa.Column("exchange_trade_id", sa.Text(), primary_key=True),
    )


def downgrade() -> None:
    # Best-effort baseline downgrade.
    op.drop_table("deal_trade_refs")
    op.drop_table("deal_fills")
    op.drop_index("ix_deals_closed_at", table_name="deals")
    op.drop_index("ix_deals_position_id", table_name="deals")
    op.drop_index("ix_deals_bot_run_id", table_name="deals")
    op.drop_table("deals")

    op.drop_index("ix_pnl_ledger_entries_position_id", table_name="pnl_ledger_entries")
    op.drop_index("ix_pnl_ledger_entries_bot_run_id", table_name="pnl_ledger_entries")
    op.drop_table("pnl_ledger_entries")

    op.drop_index("ix_lot_allocations_closing_fill_id", table_name="lot_allocations")
    op.drop_table("lot_allocations")
    op.drop_index("ix_position_lots_position_id", table_name="position_lots")
    op.drop_table("position_lots")

    op.drop_index("ix_position_snapshots_position_id", table_name="position_snapshots")
    op.drop_table("position_snapshots")

    op.drop_index("ix_positions_bot_run_id", table_name="positions")
    op.drop_table("positions")

    op.drop_index("ix_trade_fills_bot_run_id", table_name="trade_fills")
    op.drop_table("trade_fills")

    op.drop_index("ix_orders_bot_run_id", table_name="orders")
    op.drop_table("orders")

    op.drop_table("instruments")

    op.drop_index("ix_bot_capital_allocation_bot_run_id", table_name="bot_capital_allocation")
    op.drop_table("bot_capital_allocation")

    op.drop_index("ix_bot_runs_bot_id", table_name="bot_runs")
    op.drop_table("bot_runs")

    op.drop_index("ix_bot_configs_bot_id", table_name="bot_configs")
    op.drop_table("bot_configs")

    op.drop_index("ix_bots_user_id", table_name="bots")
    op.drop_table("bots")

