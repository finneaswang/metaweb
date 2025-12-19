# open_webui/metaweb/routers/assignments.py
# Assignment Management API Endpoints

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import logging
import io

from ..models.assignment import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
    AssignmentStatus
)
from ..services import db_service, file_storage, cache, ai_service
from open_webui.utils.auth import get_current_user, get_teacher_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metaweb/assignments", tags=["assignments"])




@router.post("", response_model=AssignmentResponse)
async def create_assignment(
    assignment: AssignmentCreate,
    user=Depends(get_teacher_user)
):
    """Create new assignment (teacher/admin only)"""
    try:
        if user.role not in {"teacher", "leader", "admin"}:
            raise HTTPException(status_code=403, detail="Not authorized: teacher role required")

        # Generate assignment ID
        assignment_id = str(uuid.uuid4())

        # Prepare assignment data
        assignment_data = {
            'id': assignment_id,
            'teacher_id': user.id,
            'title': assignment.title,
            'description': assignment.description,
            'subject': assignment.subject,
            'grade_level': assignment.grade_level,
            'due_date': assignment.due_date.isoformat(),
            'allow_late_submission': assignment.allow_late_submission,
            'late_penalty_percent': assignment.late_penalty_percent,
            'total_points': assignment.total_points,
            'grading_mode': assignment.grading_mode.value,
            'grading_rubric': assignment.grading_rubric,
            'target_type': assignment.target_type,
            'target_ids': assignment.target_ids,
            'allow_student_view_others': assignment.allow_student_view_others,
            'allow_comments': assignment.allow_comments,
            'enable_ocr': assignment.enable_ocr,
            'status': 'draft'
        }

        # Save to database
        result = db_service.create_assignment(assignment_data)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create assignment")

        # Fetch and return the created assignment
        created = db_service.get_assignment(assignment_id)

        return AssignmentResponse(**created)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: str,
    user=Depends(get_teacher_user)
):
    """Get assignment details"""
    try:
        # Check cache first
        cache_key = f"assignment:{assignment_id}"
        cached = cache.get(cache_key)

        if cached:
            return AssignmentResponse(**cached)

        # Fetch from database
        assignment = db_service.get_assignment(assignment_id)

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        # Cache for 5 minutes
        cache.set(cache_key, assignment, ttl=300)

        return AssignmentResponse(**assignment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[AssignmentResponse])
async def list_assignments(
    status: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_teacher_user)
):
    """List assignments"""
    try:
        # For teachers: show their own assignments
        # For students: show published assignments they can access
        # TODO: Add role-based filtering

        assignments = db_service.list_assignments(
            teacher_id=user.id if user.role in {"teacher", "leader", "admin"} else None,
            status=status,
            limit=limit,
            offset=offset
        )

        return [AssignmentResponse(**a) for a in assignments]

    except Exception as e:
        logger.error(f"Error listing assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: str,
    updates: AssignmentUpdate,
    user=Depends(get_teacher_user)
):
    """Update assignment (teacher only)"""
    try:
        # Verify assignment exists and user owns it
        assignment = db_service.get_assignment(assignment_id)

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if assignment['teacher_id'] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Prepare updates
        update_data = updates.dict(exclude_unset=True)

        # Convert enums to strings
        if 'grading_mode' in update_data:
            update_data['grading_mode'] = update_data['grading_mode'].value
        if 'status' in update_data:
            update_data['status'] = update_data['status'].value
        if 'due_date' in update_data:
            update_data['due_date'] = update_data['due_date'].isoformat()

        # Update database
        success = db_service.update_assignment(assignment_id, update_data)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update assignment")

        # Clear cache
        cache.delete(f"assignment:{assignment_id}")

        # Return updated assignment
        updated = db_service.get_assignment(assignment_id)
        return AssignmentResponse(**updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{assignment_id}/publish")
async def publish_assignment(
    assignment_id: str,
    user=Depends(get_teacher_user)
):
    """Publish assignment to students"""
    try:
        assignment = db_service.get_assignment(assignment_id)

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if assignment['teacher_id'] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        if assignment['status'] != 'draft':
            raise HTTPException(status_code=400, detail="Assignment already published")

        # Update status to published
        success = db_service.update_assignment(
            assignment_id,
            {
                'status': 'published',
                'publish_date': datetime.now().isoformat()
            }
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to publish assignment")

        # Clear cache
        cache.delete(f"assignment:{assignment_id}")

        return {"message": "Assignment published successfully", "assignment_id": assignment_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{assignment_id}/files")
async def upload_assignment_file(
    assignment_id: str,
    file: UploadFile = File(...),
    user=Depends(get_teacher_user)
):
    """Upload assignment file (question paper, materials, etc.)"""
    try:
        # Verify assignment exists and user owns it
        assignment = db_service.get_assignment(assignment_id)

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if assignment['teacher_id'] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Read file data
        file_data = await file.read()
        file_stream = io.BytesIO(file_data)

        # Upload to MinIO
        uploaded = file_storage.upload_file(
            file_data=file_stream,
            file_name=file.filename,
            content_type=file.content_type,
            folder=f"assignments/{assignment_id}"
        )

        # TODO: Update assignment files field in database

        return {
            "message": "File uploaded successfully",
            "file": uploaded
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assignment_id}/submissions/stats")
async def get_submission_stats(
    assignment_id: str,
    user=Depends(get_teacher_user)
):
    """Get submission statistics for an assignment (teacher only)"""
    try:
        # Verify assignment exists and user owns it
        assignment = db_service.get_assignment(assignment_id)

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if assignment['teacher_id'] != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Get all submissions for this assignment
        submissions = db_service.list_submissions(assignment_id=assignment_id)

        total = len(submissions)
        graded = len([s for s in submissions if s['status'] == 'graded'])
        pending = len([s for s in submissions if s['status'] in ['submitted', 'ai_reviewed']])

        scores = [s.get('teacher_score') or s.get('ai_score', 0) for s in submissions if s.get('teacher_score') or s.get('ai_score')]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "assignment_id": assignment_id,
            "total_submissions": total,
            "graded_count": graded,
            "pending_count": pending,
            "average_score": round(avg_score, 2),
            "submission_rate": round(total / 100 * 100, 1)  # TODO: Get actual student count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching submission stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
