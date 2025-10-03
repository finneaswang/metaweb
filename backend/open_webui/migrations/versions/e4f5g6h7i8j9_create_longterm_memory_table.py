"""Create longterm_memory table for AI-powered student profiles

Revision ID: e4f5g6h7i8j9
Revises: d3e4f5g6h7i8
Create Date: 2025-10-03 08:30:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e4f5g6h7i8j9"
down_revision: Union[str, None] = "d3e4f5g6h7i8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "longterm_memory",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("tags", sa.JSON(), server_default="[]"),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    
    # 创建索引
    op.create_index("longterm_memory_user_idx", "longterm_memory", ["user_id"])
    op.create_index("longterm_memory_namespace_idx", "longterm_memory", ["namespace"])
    op.create_index("longterm_memory_user_namespace_idx", "longterm_memory", ["user_id", "namespace"])


def downgrade():
    op.drop_index("longterm_memory_user_namespace_idx", table_name="longterm_memory")
    op.drop_index("longterm_memory_namespace_idx", table_name="longterm_memory")
    op.drop_index("longterm_memory_user_idx", table_name="longterm_memory")
    op.drop_table("longterm_memory")
