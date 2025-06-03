"""Initial migration

Revision ID: 1cada2bd4e38
Revises:
Create Date: 2025-03-09 21:06:24.037312

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1cada2bd4e38"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "logchat_user",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_logchat_user_id"), "logchat_user", ["id"], unique=False)
    op.create_table(
        "thread",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("thread_name", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["logchat_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_thread_user_id"), "thread", ["user_id"], unique=False)
    op.create_table(
        "log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("timestamp", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("occurred_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "log_type",
            sa.Enum("SYMPTOM", "EXPERIENCE", "ACTIVITY", "CONSUMPTION", name="logtype"),
            nullable=False,
        ),
        sa.Column("amount", sa.String(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("intensity", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["thread.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["logchat_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_log_thread_id"), "log", ["thread_id"], unique=False)
    op.create_index(op.f("ix_log_user_id"), "log", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_log_user_id"), table_name="log")
    op.drop_index(op.f("ix_log_thread_id"), table_name="log")
    op.drop_table("log")
    op.drop_index(op.f("ix_thread_user_id"), table_name="thread")
    op.drop_table("thread")
    op.drop_index(op.f("ix_logchat_user_id"), table_name="logchat_user")
    op.drop_table("logchat_user")
