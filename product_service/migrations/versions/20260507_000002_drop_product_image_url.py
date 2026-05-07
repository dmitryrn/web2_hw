"""drop product image_url

Revision ID: 20260507_000002
Revises: 20260418_000001
Create Date: 2026-05-07 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260507_000002"
down_revision: Union[str, None] = "20260418_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("products", "image_url")


def downgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.Text(), nullable=True))
