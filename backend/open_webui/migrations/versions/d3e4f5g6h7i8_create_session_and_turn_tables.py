"""Create session and turn tables for conversation tracking

Revision ID: d3e4f5g6h7i8
Revises: c2b3d4e5f6g7
Create Date: 2025-10-03 04:58:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d3e4f5g6h7i8"
down_revision: Union[str, None] = "c2b3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 创建 session 表
    op.create_table(
        "session",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("assignment_id", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), server_default="chat"),
        sa.Column("started_at", sa.BigInteger(), nullable=False),
        sa.Column("ended_at", sa.BigInteger(), nullable=True),
        sa.Column("policy_snapshot", sa.JSON(), server_default="{}"),
        sa.Column("meta", sa.JSON(), server_default="{}"),
    )
    
    # 创建 session 索引
    op.create_index("session_user_idx", "session", ["user_id"])
    op.create_index("session_assignment_idx", "session", ["assignment_id"])
    
    # 创建 turn 表
    op.create_table(
        "turn",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("tool_calls", sa.JSON(), server_default="[]"),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("tokens_in", sa.BigInteger(), server_default="0"),
        sa.Column("tokens_out", sa.BigInteger(), server_default="0"),
        sa.Column("cost", sa.BigInteger(), server_default="0"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("meta", sa.JSON(), server_default="{}"),
    )
    
    # 创建 turn 索引
    op.create_index("turn_session_idx", "turn", ["session_id"])
    op.create_index("turn_created_idx", "turn", ["created_at"])


def downgrade():
    # 删除 turn 表及索引
    op.drop_index("turn_created_idx", table_name="turn")
    op.drop_index("turn_session_idx", table_name="turn")
    op.drop_table("turn")
    
    # 删除 session 表及索引
    op.drop_index("session_assignment_idx", table_name="session")
    op.drop_index("session_user_idx", table_name="session")
    op.drop_table("session")
