"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = set(inspector.get_table_names())

    if "usuals" not in existing:
        op.create_table(
            "usuals",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "weekly_meals" not in existing:
        op.create_table(
            "weekly_meals",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("day_of_week", sa.Integer(), nullable=False),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("url", sa.String(), nullable=True),
            sa.Column("week_start", sa.Date(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "working_lists" not in existing:
        op.create_table(
            "working_lists",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "working_list_items" not in existing:
        op.create_table(
            "working_list_items",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "list_id",
                UUID(as_uuid=True),
                sa.ForeignKey("working_lists.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("amount", sa.String(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "recipes" not in existing:
        op.create_table(
            "recipes",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=True),
            sa.Column("notes", sa.String(), nullable=True),
            sa.Column("instructions", JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "recipe_ingredients" not in existing:
        op.create_table(
            "recipe_ingredients",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "recipe_id",
                UUID(as_uuid=True),
                sa.ForeignKey("recipes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("amount", sa.String(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
    op.drop_table("working_list_items")
    op.drop_table("working_lists")
    op.drop_table("weekly_meals")
    op.drop_table("usuals")
