import json
import time
import uuid
from typing import Optional
from functools import lru_cache

from open_webui.internal.db import Base, get_db
from open_webui.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, Integer, Float
from sqlalchemy import or_, func, select, and_, text

####################
# Submission DB Schema
####################


class Submission(Base):
    __tablename__ = "submission"

    id = Column(Text, primary_key=True)
    assignment_id = Column(Text)
    student_id = Column(Text)

    content = Column(Text, nullable=True)  # 学生提交的答案内容
    attachments = Column(JSON, nullable=True)  # 附件列表
    
    status = Column(Text, default="draft")  # draft, submitted, ai_reviewed, graded, released
    submitted_at = Column(BigInteger, nullable=True)
    
    # 成绩相关
    score = Column(Float, nullable=True)  # 最终总分
    max_score = Column(Float, nullable=True)  # 满分（从 assignment 复制）
    grade = Column(Text, nullable=True)  # 等级 A/B/C/D/F
    feedback = Column(Text, nullable=True)  # 老师评语
    
    # Rubric 分项得分
    rubric_scores_json = Column(JSON, nullable=True)  # 各项评分 {"logic": 3, "accuracy": 4.5, ...}
    
    # AI 分析
    ai_analysis = Column(JSON, nullable=True)  # AI分析结果
    ai_feedback_draft = Column(Text, nullable=True)  # AI生成的评语草稿
    
    # 批改人
    grader_id = Column(Text, nullable=True)  # 批改教师ID
    graded_at = Column(BigInteger, nullable=True)  # 批改时间

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class SubmissionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assignment_id: str
    student_id: str

    content: Optional[str] = None
    attachments: Optional[list] = None
    
    status: str = "draft"
    submitted_at: Optional[int] = None
    
    score: Optional[float] = None
    max_score: Optional[float] = None
    grade: Optional[str] = None
    feedback: Optional[str] = None
    
    rubric_scores_json: Optional[dict] = None
    ai_analysis: Optional[dict] = None
    ai_feedback_draft: Optional[str] = None
    
    grader_id: Optional[str] = None
    graded_at: Optional[int] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class SubmissionForm(BaseModel):
    assignment_id: str
    content: Optional[str] = None
    attachments: Optional[list] = None


class SubmissionUpdateForm(BaseModel):
    content: Optional[str] = None
    attachments: Optional[list] = None
    status: Optional[str] = None
    score: Optional[float] = None
    grade: Optional[str] = None
    feedback: Optional[str] = None
    rubric_scores_json: Optional[dict] = None
    ai_analysis: Optional[dict] = None
    ai_feedback_draft: Optional[str] = None


class GradeSubmissionForm(BaseModel):
    """教师评分表单"""
    rubric_scores_json: dict  # 各项得分
    feedback: Optional[str] = None  # 评语
    adopt_ai_draft: Optional[bool] = False  # 是否采纳AI草稿


class SubmissionResponse(SubmissionModel):
    student: Optional[UserResponse] = None
    grader: Optional[UserResponse] = None


class SubmissionTable:
    def insert_new_submission(
        self,
        form_data: SubmissionForm,
        student_id: str,
        max_score: float = 100.0,
    ) -> Optional[SubmissionModel]:
        with get_db() as db:
            submission = SubmissionModel(
                **{
                    "id": str(uuid.uuid4()),
                    "student_id": student_id,
                    "max_score": max_score,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            new_submission = Submission(**submission.model_dump())

            db.add(new_submission)
            db.commit()
            return submission

    def get_submission_by_id(self, id: str) -> Optional[SubmissionModel]:
        with get_db() as db:
            submission = db.query(Submission).filter(Submission.id == id).first()
            return SubmissionModel.model_validate(submission) if submission else None

    def get_submissions_by_assignment_id(
        self, assignment_id: str
    ) -> list[SubmissionModel]:
        with get_db() as db:
            submissions = (
                db.query(Submission)
                .filter(Submission.assignment_id == assignment_id)
                .order_by(Submission.submitted_at.desc())
                .all()
            )
            return [SubmissionModel.model_validate(s) for s in submissions]

    def get_submission_by_assignment_and_student(
        self, assignment_id: str, student_id: str
    ) -> Optional[SubmissionModel]:
        with get_db() as db:
            submission = (
                db.query(Submission)
                .filter(
                    Submission.assignment_id == assignment_id,
                    Submission.student_id == student_id,
                )
                .first()
            )
            return SubmissionModel.model_validate(submission) if submission else None

    def get_submissions_by_student_id(
        self, student_id: str
    ) -> list[SubmissionModel]:
        with get_db() as db:
            submissions = (
                db.query(Submission)
                .filter(Submission.student_id == student_id)
                .order_by(Submission.updated_at.desc())
                .all()
            )
            return [SubmissionModel.model_validate(s) for s in submissions]

    def update_submission_by_id(
        self, id: str, form_data: SubmissionUpdateForm
    ) -> Optional[SubmissionModel]:
        with get_db() as db:
            submission = db.query(Submission).filter(Submission.id == id).first()
            if not submission:
                return None

            form_data_dict = form_data.model_dump(exclude_unset=True)

            for key, value in form_data_dict.items():
                setattr(submission, key, value)

            # 如果状态改为 submitted，记录提交时间
            if form_data.status == "submitted" and submission.submitted_at is None:
                submission.submitted_at = int(time.time())

            submission.updated_at = int(time.time())

            db.commit()
            return SubmissionModel.model_validate(submission)
    
    def grade_submission(
        self,
        submission_id: str,
        grader_id: str,
        rubric_scores: dict,
        feedback: Optional[str] = None,
        total_score: Optional[float] = None,
    ) -> Optional[SubmissionModel]:
        """教师评分"""
        with get_db() as db:
            submission = db.query(Submission).filter(Submission.id == submission_id).first()
            if not submission:
                return None
            
            submission.rubric_scores_json = rubric_scores
            submission.feedback = feedback
            submission.score = total_score
            submission.grader_id = grader_id
            submission.graded_at = int(time.time())
            submission.status = "graded"
            submission.updated_at = int(time.time())
            
            db.commit()
            return SubmissionModel.model_validate(submission)

    def delete_submission_by_id(self, id: str):
        with get_db() as db:
            db.query(Submission).filter(Submission.id == id).delete()
            db.commit()
            return True


Submissions = SubmissionTable()
