"""increased vector dim

Revision ID: a81360ba52a3
Revises: 768d14ebc22a
Create Date: 2025-04-18 14:51:17.599528

"""

from typing import Sequence, Union

import pgvector.sqlalchemy

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a81360ba52a3"
down_revision: Union[str, None] = "768d14ebc22a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "knowledge",
        "embedding",
        existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=512),
        type_=pgvector.sqlalchemy.vector.VECTOR(dim=768),
        existing_comment="Vector embedding of the content",
        existing_nullable=True,
        schema="knowledge",
    )


def downgrade() -> None:
    op.alter_column(
        "knowledge",
        "embedding",
        existing_type=pgvector.sqlalchemy.vector.VECTOR(dim=768),
        type_=pgvector.sqlalchemy.vector.VECTOR(dim=512),
        existing_comment="Vector embedding of the content",
        existing_nullable=True,
        schema="knowledge",
    )
