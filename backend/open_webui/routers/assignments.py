import json
import logging
import time
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel

from open_webui.socket.main import sio


from open_webui.models.users import Users, UserResponse
from open_webui.models.assignments import (
    Assignments,
    AssignmentModel,
    AssignmentForm,
    AssignmentUpdateForm,
    AssignmentUserResponse,
)

from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetAssignments
############################


@router.get("/", response_model=list[AssignmentUserResponse])
async def get_assignments(request: Request, user=Depends(get_verified_user)):
    # Get all assignments accessible to the user
    assignments = [
        AssignmentUserResponse(
            **{
                **assignment.model_dump(),
                "user": UserResponse(**Users.get_user_by_id(assignment.user_id).model_dump()),
            }
        )
        for assignment in Assignments.get_assignments_by_permission(user.id, "read")
    ]

    return assignments


class AssignmentTitleIdResponse(BaseModel):
    id: str
    title: str
    due_date: str
    status: str
    updated_at: int
    created_at: int


@router.get("/list", response_model=list[AssignmentTitleIdResponse])
async def get_assignment_list(
    request: Request, page: Optional[int] = None, user=Depends(get_verified_user)
):
    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    assignments = [
        AssignmentTitleIdResponse(**assignment.model_dump())
        for assignment in Assignments.get_assignments_by_permission(
            user.id, "read", skip=skip, limit=limit
        )
    ]

    return assignments


############################
# CreateNewAssignment
############################


@router.post("/create", response_model=Optional[AssignmentModel])
async def create_new_assignment(
    request: Request, form_data: AssignmentForm, user=Depends(get_verified_user)
):
    # Only admins can create assignments
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        assignment = Assignments.insert_new_assignment(form_data, user.id)
        return assignment
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetAssignmentById
############################


@router.get("/{id}", response_model=Optional[AssignmentModel])
async def get_assignment_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    assignment = Assignments.get_assignment_by_id(id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check if user has read access
    if user.role != "admin" and (
        user.id != assignment.user_id
        and not has_access(user.id, type="read", access_control=assignment.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    return assignment


############################
# UpdateAssignmentById
############################


@router.post("/{id}/update", response_model=Optional[AssignmentModel])
async def update_assignment_by_id(
    request: Request,
    id: str,
    form_data: AssignmentUpdateForm,
    user=Depends(get_verified_user),
):
    assignment = Assignments.get_assignment_by_id(id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only admin or assignment creator can update
    if user.role != "admin" and user.id != assignment.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        assignment = Assignments.update_assignment_by_id(id, form_data)
        await sio.emit(
            "assignment-events",
            assignment.model_dump(),
            to=f"assignment:{assignment.id}",
        )

        return assignment
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# SubmitAssignment
############################


@router.post("/{id}/submit", response_model=Optional[AssignmentModel])
async def submit_assignment(
    request: Request, id: str, user=Depends(get_verified_user)
):
    assignment = Assignments.get_assignment_by_id(id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Students can only submit assignments they have access to
    if not has_access(user.id, type="read", access_control=assignment.access_control):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        # Update assignment status to submitted
        update_form = AssignmentUpdateForm(
            status="submitted", submitted_at=int(time.time())
        )
        assignment = Assignments.update_assignment_by_id(id, update_form)

        await sio.emit(
            "assignment-events",
            assignment.model_dump(),
            to=f"assignment:{assignment.id}",
        )

        return assignment
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteAssignmentById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_assignment_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    assignment = Assignments.get_assignment_by_id(id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only admin or assignment creator can delete
    if user.role != "admin" and user.id != assignment.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        assignment = Assignments.delete_assignment_by_id(id)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
