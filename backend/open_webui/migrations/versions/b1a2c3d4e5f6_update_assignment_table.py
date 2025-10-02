"""Update assignment table for teacher-student workflow

Revision ID: b1a2c3d4e5f6
Revises: a5c220713937
Create Date: 2025-10-02 12:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, None] = "a5c220713937"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 检查表是否存在
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if "assignment" not in tables:
        # 表不存在，创建完整的新表
        op.create_table(
            "assignment",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("teacher_id", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("due_date", sa.Text(), nullable=False),
            sa.Column("max_score", sa.Float(), server_default="100.0", nullable=False),
            sa.Column("attachments", sa.JSON(), nullable=True),
            sa.Column("status", sa.Text(), server_default="draft", nullable=False),
            sa.Column("access_control", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        # 表已存在，执行更新
        with op.batch_alter_table("assignment", schema=None) as batch_op:
            batch_op.alter_column("user_id", new_column_name="teacher_id")
            batch_op.add_column(sa.Column("content", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("max_score", sa.Float(), server_default="100.0"))
            batch_op.add_column(sa.Column("attachments", sa.JSON(), nullable=True))
            batch_op.alter_column("status", server_default="draft")
            batch_op.drop_column("submitted_at")


def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("assignment")]
    
    if "teacher_id" in columns:
        # 这是新表，需要更新回旧格式或删除
        with op.batch_alter_table("assignment", schema=None) as batch_op:
            batch_op.add_column(sa.Column("submitted_at", sa.BigInteger(), nullable=True))
            batch_op.drop_column("attachments")
            batch_op.drop_column("max_score")
            batch_op.drop_column("content")
            batch_op.alter_column("teacher_id", new_column_name="user_id")
            batch_op.alter_column("status", server_default="pending")
