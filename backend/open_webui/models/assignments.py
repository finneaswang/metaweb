import json
import time
import uuid
from typing import Optional
from functools import lru_cache

from open_webui.internal.db import Base, get_db
from open_webui.models.groups import Groups
from open_webui.utils.access_control import has_access
from open_webui.models.users import Users, UserResponse


from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, Float
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# Assignment DB Schema
####################


class Assignment(Base):
    __tablename__ = "assignment"

    id = Column(Text, primary_key=True)
    teacher_id = Column(Text)  # 创建作业的老师

    title = Column(Text)
    description = Column(Text, nullable=True)  # 简短描述
    content = Column(Text, nullable=True)  # 作业内容/要求（富文本）
    due_date = Column(Text)
    
    max_score = Column(Float, default=100.0)  # 满分
    attachments = Column(JSON, nullable=True)  # 附件列表
    status = Column(Text, default="draft")  # draft, published, closed
    
    # Rubric 评分标准
    rubric_json = Column(JSON, nullable=True)  # 评分准则
    grading_formula_json = Column(JSON, nullable=True)  # 计分公式
    
    # AI 辅助开关
    ai_assist = Column(Boolean, default=False)  # 是否启用AI辅助评分

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class AssignmentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    teacher_id: str

    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    due_date: str
    
    max_score: float = 100.0
    attachments: Optional[list] = None
    status: str = "draft"
    
    rubric_json: Optional[dict] = None
    grading_formula_json: Optional[dict] = None
    ai_assist: bool = False

    access_control: Optional[dict] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class AssignmentForm(BaseModel):
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    due_date: str
    max_score: Optional[float] = 100.0
    attachments: Optional[list] = None
    status: Optional[str] = "draft"
    rubric_json: Optional[dict] = None
    grading_formula_json: Optional[dict] = None
    ai_assist: Optional[bool] = False
    access_control: Optional[dict] = None


class AssignmentUpdateForm(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    due_date: Optional[str] = None
    max_score: Optional[float] = None
    attachments: Optional[list] = None
    status: Optional[str] = None
    rubric_json: Optional[dict] = None
    grading_formula_json: Optional[dict] = None
    ai_assist: Optional[bool] = None
    access_control: Optional[dict] = None


class AssignmentUserResponse(AssignmentModel):
    teacher: Optional[UserResponse] = None
    submission_count: Optional[int] = 0  # 提交数量
    graded_count: Optional[int] = 0  # 已批改数量


class AssignmentTable:
    def insert_new_assignment(
        self,
        form_data: AssignmentForm,
        teacher_id: str,
    ) -> Optional[AssignmentModel]:
        with get_db() as db:
            assignment = AssignmentModel(
                **{
                    "id": str(uuid.uuid4()),
                    "teacher_id": teacher_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            new_assignment = Assignment(**assignment.model_dump())

            db.add(new_assignment)
            db.commit()
            return assignment

    def get_assignments(
        self, skip: Optional[int] = None, limit: Optional[int] = None
    ) -> list[AssignmentModel]:
        with get_db() as db:
            query = db.query(Assignment).order_by(Assignment.updated_at.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            assignments = query.all()
            return [AssignmentModel.model_validate(assignment) for assignment in assignments]

    def get_assignments_by_teacher_id(
        self,
        teacher_id: str,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[AssignmentModel]:
        with get_db() as db:
            query = db.query(Assignment).filter(Assignment.teacher_id == teacher_id)
            query = query.order_by(Assignment.updated_at.desc())

            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            assignments = query.all()
            return [AssignmentModel.model_validate(assignment) for assignment in assignments]

    def get_assignments_by_permission(
        self,
        user_id: str,
        permission: str = "write",
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[AssignmentModel]:
        with get_db() as db:
            user_groups = Groups.get_groups_by_member_id(user_id)
            user_group_ids = {group.id for group in user_groups}

            query = (
                db.query(Assignment)
                .order_by(Assignment.updated_at.desc())
                .execution_options(stream_results=True)
                .yield_per(256)
            )

            results: list[AssignmentModel] = []
            n_skipped = 0

            for assignment in query:
                # Fast-pass #1: owner/teacher
                if assignment.teacher_id == user_id:
                    permitted = True
                # Fast-pass #2: public/open
                elif assignment.access_control is None:
                    # Public assignments can be read by everyone
                    permitted = True
                else:
                    permitted = has_access(
                        user_id, permission, assignment.access_control, user_group_ids
                    )

                if not permitted:
                    continue

                if skip and n_skipped < skip:
                    n_skipped += 1
                    continue

                results.append(AssignmentModel.model_validate(assignment))
                if limit is not None and len(results) >= limit:
                    break

            return results

    def get_assignment_by_id(self, id: str) -> Optional[AssignmentModel]:
        with get_db() as db:
            assignment = db.query(Assignment).filter(Assignment.id == id).first()
            return AssignmentModel.model_validate(assignment) if assignment else None

    def update_assignment_by_id(
        self, id: str, form_data: AssignmentUpdateForm
    ) -> Optional[AssignmentModel]:
        with get_db() as db:
            assignment = db.query(Assignment).filter(Assignment.id == id).first()
            if not assignment:
                return None

            form_data_dict = form_data.model_dump(exclude_unset=True)

            for key, value in form_data_dict.items():
                setattr(assignment, key, value)

            assignment.updated_at = int(time.time())

            db.commit()
            return AssignmentModel.model_validate(assignment) if assignment else None

    def delete_assignment_by_id(self, id: str):
        with get_db() as db:
            db.query(Assignment).filter(Assignment.id == id).delete()
            db.commit()
            return True


Assignments = AssignmentTable()
