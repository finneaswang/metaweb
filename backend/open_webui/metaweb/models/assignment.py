# open_webui/metaweb/models/assignment.py
# 作业数据模型

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class GradingMode(str, Enum):
    """批改模式"""
    MANUAL = "manual"  # 纯人工
    AI_DRAFT = "ai_draft"  # AI草稿，老师审核
    AI_AUTO = "ai_auto"  # AI自动批改


class AssignmentStatus(str, Enum):
    """作业状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class AssignmentCreate(BaseModel):
    """创建作业请求"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    subject: str = Field(..., description="科目：数学/物理/化学等")
    grade_level: Optional[str] = Field(None, description="年级：高一/高二/高三")

    due_date: datetime
    allow_late_submission: bool = False
    late_penalty_percent: float = Field(0, ge=0, le=100)

    total_points: float = Field(..., gt=0)
    grading_mode: GradingMode = GradingMode.MANUAL

    grading_rubric: Optional[str] = None
    target_type: str = Field("class", description="发布对象类型")
    target_ids: List[str] = Field(default_factory=list)

    allow_student_view_others: bool = False
    allow_comments: bool = True
    enable_ocr: bool = False


class AssignmentUpdate(BaseModel):
    """更新作业"""
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    grading_mode: Optional[GradingMode] = None
    status: Optional[AssignmentStatus] = None


class AssignmentResponse(BaseModel):
    """作业响应"""
    id: str
    teacher_id: str
    title: str
    description: Optional[str]
    subject: str
    grade_level: Optional[str]

    publish_date: datetime
    due_date: datetime
    total_points: float
    grading_mode: str

    files: List[dict] = []
    ai_analysis: Optional[dict] = None

    submission_count: int = 0
    graded_count: int = 0
    status: str

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
