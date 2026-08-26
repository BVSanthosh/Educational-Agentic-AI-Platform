"""add_pgvector_extension

Revision ID: bb89f1efee94
Revises: 
Create Date: 2026-07-29 16:05:12.060669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb89f1efee94'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # activates vector extension for postgres before any vector tables are created
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    # cleanup extension on full rollback
    op.execute("DROP EXTENSION IF EXISTS vector;")
