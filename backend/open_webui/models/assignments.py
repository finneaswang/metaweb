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
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy import or_, func, select, and_, text
from sqlalchemy.sql import exists

####################
# Assignment DB Schema
####################


class Assignment(Base):
    __tablename__ = "assignment"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)

    title = Column(Text)
    description = Column(Text, nullable=True)
    due_date = Column(Text)
    status = Column(Text, default="pending")  # pending, submitted
    submitted_at = Column(BigInteger, nullable=True)

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class AssignmentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    title: str
    description: Optional[str] = None
    due_date: str
    status: str = "pending"
    submitted_at: Optional[int] = None

    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class AssignmentForm(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: str
    status: Optional[str] = "pending"
    access_control: Optional[dict] = None


class AssignmentUpdateForm(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    submitted_at: Optional[int] = None
    access_control: Optional[dict] = None


class AssignmentUserResponse(AssignmentModel):
    user: Optional[UserResponse] = None


class AssignmentTable:
    def insert_new_assignment(
        self,
        form_data: AssignmentForm,
        user_id: str,
    ) -> Optional[AssignmentModel]:
        with get_db() as db:
            assignment = AssignmentModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
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

    def get_assignments_by_user_id(
        self,
        user_id: str,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[AssignmentModel]:
        with get_db() as db:
            query = db.query(Assignment).filter(Assignment.user_id == user_id)
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

            # Order newest-first. We stream to keep memory usage low.
            query = (
                db.query(Assignment)
                .order_by(Assignment.updated_at.desc())
                .execution_options(stream_results=True)
                .yield_per(256)
            )

            results: list[AssignmentModel] = []
            n_skipped = 0

            for assignment in query:
                # Fast-pass #1: owner
                if assignment.user_id == user_id:
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

                # Apply skip AFTER permission filtering so it counts only accessible assignments
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

            if "title" in form_data_dict:
                assignment.title = form_data_dict["title"]
            if "description" in form_data_dict:
                assignment.description = form_data_dict["description"]
            if "due_date" in form_data_dict:
                assignment.due_date = form_data_dict["due_date"]
            if "status" in form_data_dict:
                assignment.status = form_data_dict["status"]
            if "submitted_at" in form_data_dict:
                assignment.submitted_at = form_data_dict["submitted_at"]
            if "access_control" in form_data_dict:
                assignment.access_control = form_data_dict["access_control"]

            assignment.updated_at = int(time.time())

            db.commit()
            return AssignmentModel.model_validate(assignment) if assignment else None

    def delete_assignment_by_id(self, id: str):
        with get_db() as db:
            db.query(Assignment).filter(Assignment.id == id).delete()
            db.commit()
            return True


Assignments = AssignmentTable()
