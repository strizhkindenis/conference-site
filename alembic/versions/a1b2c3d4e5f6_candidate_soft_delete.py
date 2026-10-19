"""candidate soft delete

Revision ID: a1b2c3d4e5f6
Revises: 9d5c2e1b7a40
Create Date: 2025-01-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9d5c2e1b7a40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("votecandidate") as batch_op:
        batch_op.add_column(
            sa.Column(
                "deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("votecandidate") as batch_op:
        batch_op.drop_column("deleted")
