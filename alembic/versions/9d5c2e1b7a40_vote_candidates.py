"""vote candidates

Revision ID: 9d5c2e1b7a40
Revises: 2c14278aa4c9
Create Date: 2025-01-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9d5c2e1b7a40"
down_revision: str | None = "2c14278aa4c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "votecandidate",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("work_name", sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.add_column(
        "vote",
        sa.Column("candidate_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_vote_candidate_id",
        "vote",
        "votecandidate",
        ["candidate_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_vote_candidate_id", "vote", type_="foreignkey")
    op.drop_column("vote", "candidate_id")
    op.drop_table("votecandidate")
