from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from open_webui.models.users import Users, UserModel
from open_webui.models.submissions import Submissions
from open_webui.models.assignments import Assignments
from open_webui.utils.auth import get_verified_user
from datetime import datetime, timedelta
import time

router = APIRouter()

############################
# Request/Response Models  
############################

class SchoolStatistics(BaseModel):
    total_students: int
    total_teachers: int
    total_assignments: int
    total_submissions: int
    average_completion_rate: float

class TeacherPerformance(BaseModel):
    teacher_id: str
    teacher_name: str
    student_count: int
    assignment_count: int
    avg_student_score: float

############################
# Leader Dashboard APIs
############################

@router.get("/statistics", response_model=SchoolStatistics)
async def get_school_statistics(
    user: UserModel = Depends(get_verified_user)
):
    """获取全校统计数据 - Leader 专用"""
    if user.role not in ["leader", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only leaders and admins can access school statistics"
        )
    
    # 获取统计数据
    all_users = Users.get_users()
    students = [u for u in all_users.get("users", []) if u.role == "student"]
    teachers = [u for u in all_users.get("users", []) if u.role == "teacher"]
    
    all_assignments = Assignments.get_assignments()
    all_submissions = Submissions.get_submissions()
    
    # 计算完成率
    total_possible = len(students) * len(all_assignments) if students and all_assignments else 1
    completion_rate = (len(all_submissions) / total_possible * 100) if total_possible > 0 else 0
    
    return SchoolStatistics(
        total_students=len(students),
        total_teachers=len(teachers),
        total_assignments=len(all_assignments),
        total_submissions=len(all_submissions),
        average_completion_rate=round(completion_rate, 2)
    )


@router.get("/teachers/performance", response_model=List[TeacherPerformance])
async def get_teachers_performance(
    user: UserModel = Depends(get_verified_user)
):
    """获取教师绩效数据 - Leader 专用"""
    if user.role not in ["leader", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only leaders and admins can access teacher performance data"
        )
    
    all_users = Users.get_users()
    teachers = [u for u in all_users.get("users", []) if u.role == "teacher"]
    students = [u for u in all_users.get("users", []) if u.role == "student"]
    
    performance_data = []
    
    for teacher in teachers:
        # 获取该教师的作业
        teacher_assignments = [a for a in Assignments.get_assignments() if a.teacher_id == teacher.id]
        
        # 获取学生平均分
        teacher_submissions = [s for s in Submissions.get_submissions() 
                              if any(a.id == s.assignment_id for a in teacher_assignments)]
        
        avg_score = sum([s.score for s in teacher_submissions if s.score]) / len(teacher_submissions) if teacher_submissions else 0
        
        performance_data.append(TeacherPerformance(
            teacher_id=teacher.id,
            teacher_name=teacher.name,
            student_count=len(students),
            assignment_count=len(teacher_assignments),
            avg_student_score=round(avg_score, 2)
        ))
    
    return performance_data


@router.get("/students/overview")
async def get_students_overview(
    user: UserModel = Depends(get_verified_user)
):
    """获取学生总览 - Leader 专用"""
    if user.role not in ["leader", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only leaders and admins can access student overview"
        )
    
    all_users = Users.get_users()
    students = [u for u in all_users.get("users", []) if u.role == "student"]
    
    return {
        "students": [
            {
                "id": s.id,
                "name": s.name,
                "email": s.email,
                "submissions_count": len([sub for sub in Submissions.get_submissions() if sub.student_id == s.id])
            }
            for s in students
        ],
        "total": len(students)
    }


@router.get("/assignments/overview")  
async def get_assignments_overview(
    user: UserModel = Depends(get_verified_user)
):
    """获取作业总览 - Leader 专用"""
    if user.role not in ["leader", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only leaders and admins can access assignments overview"
        )
    
    all_assignments = Assignments.get_assignments()
    all_submissions = Submissions.get_submissions()
    
    return {
        "assignments": [
            {
                "id": a.id,
                "title": a.title,
                "teacher_id": a.teacher_id,
                "due_date": a.due_date,
                "submissions_count": len([s for s in all_submissions if s.assignment_id == a.id])
            }
            for a in all_assignments
        ],
        "total": len(all_assignments)
    }
