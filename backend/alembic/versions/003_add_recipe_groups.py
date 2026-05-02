"""Add recipe groups table and group_id FK on recipes

Revision ID: 003
Revises: 002
Create Date: 2026-05-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recipe_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_recipe_groups_name"),
    )
    op.add_column("recipes", sa.Column("group_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_recipes_group_id",
        "recipes", "recipe_groups",
        ["group_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_recipes_group_id", "recipes", type_="foreignkey")
    op.drop_column("recipes", "group_id")
    op.drop_table("recipe_groups")
