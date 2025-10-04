import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.socket.main import sio

from open_webui.models.users import Users, UserResponse
from open_webui.models.submissions import (
    Submissions,
    SubmissionModel,
    SubmissionForm,
    SubmissionUpdateForm,
    SubmissionResponse,
)
from open_webui.models.assignments import Assignments

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetSubmissions
############################


@router.get("/", response_model=list[SubmissionResponse])
async def get_submissions(request: Request, user=Depends(get_verified_user)):
    """
    Get submissions:
    - Teachers/Admins: Get all submissions for their assignments
    - Students: Get only their own submissions
    """
    if user.role in ["admin", "teacher"]:
        # For teachers, get all submissions for assignments they created
        assignments = Assignments.get_assignments_by_permission(user.id, "write")
        assignment_ids = [a.id for a in assignments]
        
        all_submissions = []
        for assignment_id in assignment_ids:
            submissions = Submissions.get_submissions_by_assignment_id(assignment_id)
            all_submissions.extend(submissions)
        
        # Add student info
        submissions_with_user = [
            SubmissionResponse(
                **{
                    **submission.model_dump(),
                    "student": UserResponse(**Users.get_user_by_id(submission.student_id).model_dump()),
                }
            )
            for submission in all_submissions
        ]
    else:
        # Students only see their own submissions
        submissions = Submissions.get_submissions_by_student_id(user.id)
        submissions_with_user = [
            SubmissionResponse(
                **{
                    **submission.model_dump(),
                    "student": UserResponse(**Users.get_user_by_id(submission.student_id).model_dump()),
                }
            )
            for submission in submissions
        ]

    return submissions_with_user


############################
# GetSubmissionsByAssignment
############################


@router.get("/assignment/{assignment_id}", response_model=list[SubmissionResponse])
async def get_submissions_by_assignment(
    request: Request, assignment_id: str, user=Depends(get_verified_user)
):
    """
    Get all submissions for a specific assignment.
    Only teachers/admins who own the assignment can access this.
    """
    # Check if assignment exists
    assignment = Assignments.get_assignment_by_id(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only teachers/admins who created the assignment can see all submissions
    if user.role not in ["admin", "teacher"] or assignment.teacher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    submissions = Submissions.get_submissions_by_assignment_id(assignment_id)
    
    submissions_with_user = [
        SubmissionResponse(
            **{
                **submission.model_dump(),
                "student": UserResponse(**Users.get_user_by_id(submission.student_id).model_dump()) if submission.student_id else None,
            }
        )
        for submission in submissions
    ]

    return submissions_with_user


############################
# GetSubmissionById
############################


@router.get("/{id}", response_model=Optional[SubmissionResponse])
async def get_submission_by_id(
    request: Request, id: str, user=Depends(get_verified_user)
):
    submission = Submissions.get_submission_by_id(id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check permissions
    assignment = Assignments.get_assignment_by_id(submission.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Students can only see their own submissions
    # Teachers can see submissions for their assignments
    if user.role == "student" and submission.student_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )
    
    if user.role == "teacher" and assignment.teacher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    return SubmissionResponse(
        **{
            **submission.model_dump(),
            "student": UserResponse(**Users.get_user_by_id(submission.student_id).model_dump()),
        }
    )


############################
# CreateSubmission
############################


@router.post("/create", response_model=Optional[SubmissionModel])
async def create_submission(
    request: Request, form_data: SubmissionForm, user=Depends(get_verified_user)
):
    """
    Create a new submission. Students create submissions for assignments.
    """
    # Check if assignment exists
    assignment = Assignments.get_assignment_by_id(form_data.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Check if student already has a submission for this assignment
    existing = Submissions.get_submission_by_assignment_and_student(
        form_data.assignment_id, user.id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission already exists for this assignment"
        )

    try:
        submission = Submissions.insert_new_submission(
            form_data, 
            user.id,
            max_score=assignment.max_score
        )
        return submission
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# UpdateSubmission
############################


@router.post("/{id}/update", response_model=Optional[SubmissionModel])
async def update_submission(
    request: Request,
    id: str,
    form_data: SubmissionUpdateForm,
    user=Depends(get_verified_user),
):
    """
    Update a submission.
    - Students can update their own draft submissions (content, attachments)
    - Teachers can update score, grade, feedback for submissions of their assignments
    """
    submission = Submissions.get_submission_by_id(id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Get the assignment
    assignment = Assignments.get_assignment_by_id(submission.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Permission check
    is_student_owner = user.role == "student" and submission.student_id == user.id
    is_teacher_owner = user.role in ["teacher", "admin"] and assignment.teacher_id == user.id

    if not is_student_owner and not is_teacher_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    # Students can only edit draft submissions and only content/attachments
    if is_student_owner and submission.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit submitted assignments"
        )

    # Students cannot modify grading fields
    if is_student_owner:
        restricted_fields = {"score", "grade", "feedback", "ai_analysis", "status"}
        submitted_fields = set(form_data.model_dump(exclude_unset=True).keys())
        if restricted_fields & submitted_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot modify grading fields"
            )

    try:
        submission = Submissions.update_submission_by_id(id, form_data)
        
        await sio.emit(
            "submission-events",
            submission.model_dump(),
            to=f"submission:{submission.id}",
        )

        return submission
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# SubmitSubmission
############################


@router.post("/{id}/submit", response_model=Optional[SubmissionModel])
async def submit_submission(
    request: Request, id: str, user=Depends(get_verified_user)
):
    """
    Submit a submission (change status from draft to submitted).
    Only the student who owns the submission can submit it.
    """
    submission = Submissions.get_submission_by_id(id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only the student who owns the submission can submit
    if submission.student_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    # Can only submit draft submissions
    if submission.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission has already been submitted"
        )

    try:
        update_form = SubmissionUpdateForm(status="submitted")
        submission = Submissions.update_submission_by_id(id, update_form)

        await sio.emit(
            "submission-events",
            submission.model_dump(),
            to=f"submission:{submission.id}",
        )

        return submission
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GradeSubmission
############################


class GradeForm(BaseModel):
    score: Optional[float] = None  # 总分（可选，可从rubric_scores计算）
    grade: Optional[str] = None
    feedback: Optional[str] = None
    rubric_scores: Optional[dict] = None  # Rubric各项得分 {"logic": 3, "accuracy": 4.5}
    adopt_ai_draft: Optional[bool] = False  # 是否采纳AI草稿


@router.post("/{id}/grade", response_model=Optional[SubmissionModel])
async def grade_submission(
    request: Request,
    id: str,
    form_data: GradeForm,
    user=Depends(get_verified_user),
):
    """
    Grade a submission. Only teachers who own the assignment can grade.
    """
    submission = Submissions.get_submission_by_id(id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Get the assignment
    assignment = Assignments.get_assignment_by_id(submission.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Only teachers/admins who created the assignment can grade
    if user.role not in ["admin", "teacher"] or assignment.teacher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        # Calculate total score from rubric if not provided
        if form_data.rubric_scores and not form_data.score:
            # Simple average for now, can be enhanced with weighted formula
            rubric_values = [v for v in form_data.rubric_scores.values() if isinstance(v, (int, float))]
            if rubric_values and assignment.max_score:
                avg_rubric_score = sum(rubric_values) / len(rubric_values)
                form_data.score = (avg_rubric_score / 5.0) * assignment.max_score  # Assume 0-5 scale
        
        update_form = SubmissionUpdateForm(
            score=form_data.score,
            grade=form_data.grade,
            feedback=form_data.feedback,
            rubric_scores_json=form_data.rubric_scores,
            status="graded"
        )
        submission = Submissions.update_submission_by_id(id, update_form)

        await sio.emit(
            "submission-events",
            submission.model_dump(),
            to=f"submission:{submission.id}",
        )

        return submission
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteSubmission
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_submission(
    request: Request, id: str, user=Depends(get_verified_user)
):
    """
    Delete a submission.
    - Students can delete their own draft submissions
    - Teachers/admins can delete submissions for their assignments
    """
    submission = Submissions.get_submission_by_id(id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Get the assignment
    assignment = Assignments.get_assignment_by_id(submission.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Permission check
    is_student_owner = user.role == "student" and submission.student_id == user.id and submission.status == "draft"
    is_teacher_owner = user.role in ["teacher", "admin"] and assignment.teacher_id == user.id

    if not is_student_owner and not is_teacher_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        Submissions.delete_submission_by_id(id)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=ERROR_MESSAGES.DEFAULT()
        )
