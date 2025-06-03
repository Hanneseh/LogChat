"""initial migration

Revision ID: 768d14ebc22a
Revises:
Create Date: 2025-04-18 12:43:45.176816

"""

from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "768d14ebc22a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "source",
            sa.String(),
            nullable=True,
            comment="Origin of the knowledge chunk (e.g., filename, URL)",
        ),
        sa.Column(
            "headline",
            sa.String(),
            nullable=True,
            comment="Headline or title associated with the chunk",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="The actual text content of the chunk",
        ),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=512),
            nullable=True,
            comment="Vector embedding of the content",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="knowledge",
    )
    op.create_index(
        op.f("ix_knowledge_knowledge_id"),
        "knowledge",
        ["id"],
        unique=False,
        schema="knowledge",
    )
    op.create_table(
        "logchat_user",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="user_data",
    )
    op.create_index(
        op.f("ix_user_data_logchat_user_id"),
        "logchat_user",
        ["id"],
        unique=False,
        schema="user_data",
    )
    op.create_table(
        "thread",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("timestamp", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_data.logchat_user.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="user_data",
    )
    op.create_index(
        op.f("ix_user_data_thread_user_id"),
        "thread",
        ["user_id"],
        unique=False,
        schema="user_data",
    )
    op.create_table(
        "log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("timestamp", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("occurred_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "log_type", sa.Enum("SYMPTOM", "ACTIVITY", name="logtype"), nullable=False
        ),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("intensity", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["user_data.thread.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_data.logchat_user.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="user_data",
    )
    op.create_index(
        op.f("ix_user_data_log_thread_id"),
        "log",
        ["thread_id"],
        unique=False,
        schema="user_data",
    )
    op.create_index(
        op.f("ix_user_data_log_user_id"),
        "log",
        ["user_id"],
        unique=False,
        schema="user_data",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_data_log_user_id"), table_name="log", schema="user_data"
    )
    op.drop_index(
        op.f("ix_user_data_log_thread_id"), table_name="log", schema="user_data"
    )
    op.drop_table("log", schema="user_data")
    op.drop_index(
        op.f("ix_user_data_thread_user_id"), table_name="thread", schema="user_data"
    )
    op.drop_table("thread", schema="user_data")
    op.drop_index(
        op.f("ix_user_data_logchat_user_id"),
        table_name="logchat_user",
        schema="user_data",
    )
    op.drop_table("logchat_user", schema="user_data")
    op.drop_index(
        op.f("ix_knowledge_knowledge_id"), table_name="knowledge", schema="knowledge"
    )
    op.drop_table("knowledge", schema="knowledge")
