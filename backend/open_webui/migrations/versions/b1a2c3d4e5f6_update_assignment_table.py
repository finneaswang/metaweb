"""Update assignment table for teacher-student workflow

Revision ID: b1a2c3d4e5f6
Revises: a5c220713937
Create Date: 2025-10-02 12:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, None] = "a5c220713937"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 重命名 user_id 为 teacher_id
    with op.batch_alter_table("assignment", schema=None) as batch_op:
        batch_op.alter_column("user_id", new_column_name="teacher_id")
        
        # 添加新字段
        batch_op.add_column(sa.Column("content", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("max_score", sa.Float(), server_default="100.0"))
        batch_op.add_column(sa.Column("attachments", sa.JSON(), nullable=True))
        
        # 修改 status 字段的默认值（从 pending 改为 draft）
        batch_op.alter_column("status", server_default="draft")
        
        # 删除不再需要的字段
        batch_op.drop_column("submitted_at")


def downgrade():
    with op.batch_alter_table("assignment", schema=None) as batch_op:
        # 恢复旧字段
        batch_op.add_column(sa.Column("submitted_at", sa.BigInteger(), nullable=True))
        
        # 删除新字段
        batch_op.drop_column("attachments")
        batch_op.drop_column("max_score")
        batch_op.drop_column("content")
        
        # 恢复原来的列名
        batch_op.alter_column("teacher_id", new_column_name="user_id")
        
        # 恢复 status 默认值
        batch_op.alter_column("status", server_default="pending")
