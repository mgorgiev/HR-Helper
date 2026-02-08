"""add resume parsing fields

Revision ID: a1b2c3d4e5f6
Revises: 679b598f8acb
Create Date: 2026-02-08 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "679b598f8acb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add AI parsing columns to resumes table."""
    op.add_column(
        "resumes",
        sa.Column("parsed_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "resumes",
        sa.Column(
            "parsed_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "resumes",
        sa.Column(
            "parsing_status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "resumes",
        sa.Column("parsing_error", sa.String(), nullable=True),
    )
    op.create_index(
        op.f("ix_resumes_parsing_status"),
        "resumes",
        ["parsing_status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove AI parsing columns from resumes table."""
    op.drop_index(op.f("ix_resumes_parsing_status"), table_name="resumes")
    op.drop_column("resumes", "parsing_error")
    op.drop_column("resumes", "parsing_status")
    op.drop_column("resumes", "parsed_at")
    op.drop_column("resumes", "parsed_data")
