# open_webui/metaweb/models/submission.py
# 学生提交数据模型

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SubmissionStatus(str, Enum):
    """提交状态"""
    SUBMITTED = "submitted"
    AI_REVIEWING = "ai_reviewing"
    AI_REVIEWED = "ai_reviewed"
    TEACHER_REVIEWING = "teacher_reviewing"
    GRADED = "graded"
    RETURNED = "returned"


class SubmissionCreate(BaseModel):
    """创建提交"""
    assignment_id: str
    answer_type: str = Field("file", description="file/text/mixed")
    answer_files: List[dict] = Field(default_factory=list)
    answer_text: Optional[str] = None
    time_spent_seconds: Optional[int] = None


class GradingResult(BaseModel):
    """批改结果"""
    score: float
    feedback: str
    detailed_analysis: Optional[dict] = None


class SubmissionUpdate(BaseModel):
    """更新提交（老师批改）"""
    teacher_score: Optional[float] = None
    teacher_feedback: Optional[str] = None
    teacher_detailed_comments: Optional[dict] = None
    status: Optional[str] = None


class SubmissionResponse(BaseModel):
    """提交响应"""
    id: str
    assignment_id: str
    student_id: str

    answer_type: str
    answer_files: List[dict]
    answer_text: Optional[str]

    ai_score: Optional[float]
    ai_feedback: Optional[str]
    ai_graded_at: Optional[datetime]

    teacher_score: Optional[float]
    teacher_feedback: Optional[str]
    teacher_graded_at: Optional[datetime]

    status: str
    submitted_at: datetime
    is_late: bool

    class Config:
        from_attributes = True
