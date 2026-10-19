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
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if not inspector.has_table("votecandidate"):
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

    inspector = sa.inspect(connection)
    vote_columns = {column["name"] for column in inspector.get_columns("vote")}
    foreign_keys = inspector.get_foreign_keys("vote")
    has_candidate_foreign_key = any(
        foreign_key.get("constrained_columns") == ["candidate_id"]
        and foreign_key.get("referred_table") == "votecandidate"
        for foreign_key in foreign_keys
    )

    if "candidate_id" not in vote_columns or not has_candidate_foreign_key:
        with op.batch_alter_table("vote") as batch_op:
            if "candidate_id" not in vote_columns:
                batch_op.add_column(
                    sa.Column("candidate_id", sa.Integer(), nullable=True)
                )
            if not has_candidate_foreign_key:
                batch_op.create_foreign_key(
                    "fk_vote_candidate_id",
                    "votecandidate",
                    ["candidate_id"],
                    ["id"],
                )


def downgrade() -> None:
    with op.batch_alter_table("vote") as batch_op:
        batch_op.drop_constraint("fk_vote_candidate_id", type_="foreignkey")
        batch_op.drop_column("candidate_id")
    op.drop_table("votecandidate")
