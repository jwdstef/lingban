"""character color bigint

Revision ID: 002_character_color_bigint
Revises: 001_initial
Create Date: 2026-07-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_character_color_bigint"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "characters",
        "color",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        existing_server_default=sa.text("0"),
    )


def downgrade() -> None:
    op.alter_column(
        "characters",
        "color",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
        existing_server_default=sa.text("0"),
        postgresql_using=(
            "CASE WHEN color > 2147483647 OR color < -2147483648 "
            "THEN 0 ELSE color END"
        ),
    )
