"""Add tags column to recipes

Revision ID: 004
Revises: 003
Create Date: 2026-05-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("tags", JSONB, nullable=True))
    op.create_index("idx_recipes_tags", "recipes", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("idx_recipes_tags", table_name="recipes")
    op.drop_column("recipes", "tags")
