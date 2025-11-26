"""Add expires_at column to trx_exchange_orders"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa


revision = "002_add_trx_exchange_expires_at"
down_revision = "001_admin_tables"
branch_labels = None
depends_on = None


TRX_EXCHANGE_TIMEOUT_DEFAULT_MINUTES = 30


def _backfill_expires_at(connection):
    """Populate expires_at for existing TRX exchange orders."""

    rows = connection.execute(
        sa.text("SELECT order_id, created_at FROM trx_exchange_orders")
    ).fetchall()

    if not rows:
        return

    for order_id, created_at in rows:
        base_created = created_at or datetime.now(timezone.utc)
        expires_at = base_created + timedelta(minutes=TRX_EXCHANGE_TIMEOUT_DEFAULT_MINUTES)
        connection.execute(
            sa.text(
                "UPDATE trx_exchange_orders SET expires_at = :expires WHERE order_id = :order_id"
            ),
            {"expires": expires_at, "order_id": order_id},
        )


def upgrade():
    op.add_column(
        "trx_exchange_orders",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    connection = op.get_bind()
    _backfill_expires_at(connection)


def downgrade():
    op.drop_column("trx_exchange_orders", "expires_at")
