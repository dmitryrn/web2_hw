"""initial schema

Revision ID: 20260418_000001
Revises:
Create Date: 2026-04-18 18:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260418_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


order_status = postgresql.ENUM(
    "created",
    "confirmed",
    "delivering",
    "delivered",
    "cancelled",
    name="order_status",
    create_type=False,
)


def upgrade() -> None:
    order_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("customer_city", sa.String(length=120), nullable=False),
        sa.Column("customer_street", sa.String(length=120), nullable=False),
        sa.Column("customer_house", sa.String(length=32), nullable=False),
        sa.Column("customer_building", sa.String(length=32), nullable=True),
        sa.Column("status", order_status, server_default="created", nullable=False),
        sa.Column("cancellation_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "product_price >= 0", name="order_items_product_price_check"
        ),
        sa.CheckConstraint("quantity > 0", name="order_items_quantity_check"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_table("orders")
    order_status.drop(op.get_bind(), checkfirst=True)
