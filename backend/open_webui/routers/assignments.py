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
                "teacher": UserResponse(**Users.get_user_by_id(assignment.teacher_id).model_dump()),
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
    # Only admins and teachers can create assignments
    if user.role not in ["admin", "teacher"]:
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
        user.id != assignment.teacher_id
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
    if user.role != "admin" and user.id != assignment.teacher_id:
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
    if user.role != "admin" and user.id != assignment.teacher_id:
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


############################
# GetAssignmentStatistics
############################


@router.get("/{id}/statistics")
async def get_assignment_statistics(id: str, user=Depends(get_verified_user)):
    """
    获取作业统计信息：提交率、平均分、成绩分布等
    """
    assignment = Assignments.get_assignment_by_id(id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check permission
    if user.role not in ["admin", "teacher"] and user.id != assignment.teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        from open_webui.models.submissions import Submissions
        from open_webui.models.users import Users

        # Get all submissions for this assignment
        submissions = Submissions.get_submissions_by_assignment_id(id)

        # Get all students
        all_users = Users.get_users()
        students = [u for u in all_users if u.role == "student"]
        total_students = len(students)

        # Calculate statistics
        submitted_count = len([s for s in submissions if s.status in ["submitted", "graded"]])
        graded_count = len([s for s in submissions if s.status == "graded"])
        
        # Score statistics
        scores = [s.score for s in submissions if s.score is not None and s.status == "graded"]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        max_score = max(scores) if scores else 0
        min_score = min(scores) if scores else 0

        # Grade distribution
        grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for s in submissions:
            if s.grade and s.grade in grade_counts:
                grade_counts[s.grade] += 1

        return {
            "assignment_id": id,
            "total_students": total_students,
            "submitted_count": submitted_count,
            "graded_count": graded_count,
            "submission_rate": round(submitted_count / total_students * 100, 1) if total_students > 0 else 0,
            "avg_score": avg_score,
            "max_score": max_score,
            "min_score": min_score,
            "grade_distribution": grade_counts
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ExportAssignmentGrades
############################


@router.get("/{id}/export")
async def export_assignment_grades(id: str, user=Depends(get_verified_user)):
    """
    导出作业成绩为 CSV 格式
    """
    assignment = Assignments.get_assignment_by_id(id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check permission
    if user.role not in ["admin", "teacher"] and user.id != assignment.teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        from open_webui.models.submissions import Submissions
        from open_webui.models.users import Users
        from fastapi.responses import StreamingResponse
        import io
        import csv
        from datetime import datetime

        # Get all submissions
        submissions = Submissions.get_submissions_by_assignment_id(id)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "学生姓名",
            "学生邮箱",
            "提交状态",
            "得分",
            "等级",
            "提交时间",
            "批改时间"
        ])
        
        # Write data
        for submission in submissions:
            student = Users.get_user_by_id(submission.student_id)
            if not student:
                continue
                
            submitted_at = datetime.fromtimestamp(submission.submitted_at).strftime("%Y-%m-%d %H:%M") if submission.submitted_at else ""
            graded_at = datetime.fromtimestamp(submission.graded_at).strftime("%Y-%m-%d %H:%M") if submission.graded_at else ""
            
            writer.writerow([
                student.name,
                student.email,
                "已提交" if submission.status == "submitted" else "已批改" if submission.status == "graded" else "草稿",
                submission.score if submission.score is not None else "",
                submission.grade or "",
                submitted_at,
                graded_at
            ])
        
        # Prepare response
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=assignment_{id}_grades.csv"
            }
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
