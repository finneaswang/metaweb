"""Create usage_log table for cost tracking

Revision ID: f5g6h7i8j9k0
Revises: e4f5g6h7i8j9
Create Date: 2025-10-03 08:35:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f5g6h7i8j9k0"
down_revision: Union[str, None] = "e4f5g6h7i8j9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "usage_log",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), server_default="chat"),
        sa.Column("tokens_in", sa.BigInteger(), server_default="0"),
        sa.Column("tokens_out", sa.BigInteger(), server_default="0"),
        sa.Column("cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("turn_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("metadata", sa.JSON(), server_default="{}"),
    )
    
    # 创建索引
    op.create_index("usage_log_user_idx", "usage_log", ["user_id"])
    op.create_index("usage_log_created_idx", "usage_log", ["created_at"])
    op.create_index("usage_log_user_created_idx", "usage_log", ["user_id", "created_at"])


def downgrade():
    op.drop_index("usage_log_user_created_idx", table_name="usage_log")
    op.drop_index("usage_log_created_idx", table_name="usage_log")
    op.drop_index("usage_log_user_idx", table_name="usage_log")
    op.drop_table("usage_log")
