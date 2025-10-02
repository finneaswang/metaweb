"""Create submission table for student assignments

Revision ID: c2b3d4e5f6g7
Revises: b1a2c3d4e5f6
Create Date: 2025-10-02 12:01:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c2b3d4e5f6g7"
down_revision: Union[str, None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "submission",
        sa.Column("id", sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column("assignment_id", sa.Text(), nullable=False),
        sa.Column("student_id", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("attachments", sa.JSON(), nullable=True),
        sa.Column("status", sa.Text(), server_default="draft"),
        sa.Column("submitted_at", sa.BigInteger(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Float(), nullable=True),
        sa.Column("grade", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("ai_analysis", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    
    # 创建索引以提高查询性能
    op.create_index(
        "ix_submission_assignment_id",
        "submission",
        ["assignment_id"],
    )
    op.create_index(
        "ix_submission_student_id",
        "submission",
        ["student_id"],
    )
    op.create_index(
        "ix_submission_assignment_student",
        "submission",
        ["assignment_id", "student_id"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_submission_assignment_student", table_name="submission")
    op.drop_index("ix_submission_student_id", table_name="submission")
    op.drop_index("ix_submission_assignment_id", table_name="submission")
    op.drop_table("submission")
