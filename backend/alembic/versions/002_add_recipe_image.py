"""Add image columns to recipes

Revision ID: 002
Revises: 001
Create Date: 2026-04-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("image_data", sa.LargeBinary(), nullable=True))
    op.add_column("recipes", sa.Column("image_content_type", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("recipes", "image_content_type")
    op.drop_column("recipes", "image_data")
