"""
MetaWeb Student Profile API Routes
学生画像查询API
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import text

from open_webui.internal.db import Session, get_db
from open_webui.utils.auth import get_current_user
from open_webui.models.users import Users

log = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class KnowledgePointProfile(BaseModel):
    id: str
    student_id: str
    subject: str
    knowledge_point: str
    total_attempts: int
    correct_attempts: int
    mastery_level: float
    recent_trend: str
    first_encountered: Optional[str]
    last_practiced: Optional[str]
    updated_at: Optional[str]


class LearningReport(BaseModel):
    id: str
    student_id: str
    report_type: str
    subject: Optional[str]
    period_start: str
    period_end: str
    summary: Optional[str]
    strengths: Optional[str]
    weaknesses: Optional[str]
    recommendations: Optional[str]
    generated_by: str
    generated_at: str


class StudentProfileSummary(BaseModel):
    student_id: str
    student_name: str
    total_knowledge_points: int
    mastered_count: int  # mastery_level >= 0.8
    learning_count: int  # 0.5 <= mastery_level < 0.8
    weak_count: int  # mastery_level < 0.5
    latest_report_date: Optional[str]


@router.get("/students/{student_id}/profile/summary")
async def get_student_profile_summary(
    student_id: str,
    user: Users = Depends(get_current_user)
):
    """
    获取学生画像摘要

    权限:
    - admin/leader/teacher: 可查看所有学生
    - student: 只能查看自己
    """
    # 权限检查
    if user.role not in ['admin', 'leader', 'teacher']:
        if user.id != student_id:
            raise HTTPException(status_code=403, detail="Permission denied")

    session = next(get_db())

    try:
        # 获取学生信息
        student_query = text("SELECT id, name FROM user WHERE id = :student_id")
        student_result = session.execute(student_query, {'student_id': student_id}).fetchone()

        if not student_result:
            raise HTTPException(status_code=404, detail="Student not found")

        # 统计知识点
        stats_query = text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN mastery_level >= 0.8 THEN 1 ELSE 0 END) as mastered,
                SUM(CASE WHEN mastery_level >= 0.5 AND mastery_level < 0.8 THEN 1 ELSE 0 END) as learning,
                SUM(CASE WHEN mastery_level < 0.5 THEN 1 ELSE 0 END) as weak
            FROM student_knowledge_profile
            WHERE student_id = :student_id
        """)
        stats_result = session.execute(stats_query, {'student_id': student_id}).fetchone()

        # 获取最新报告日期
        report_query = text("""
            SELECT period_end
            FROM learning_reports
            WHERE student_id = :student_id
            ORDER BY period_end DESC
            LIMIT 1
        """)
        report_result = session.execute(report_query, {'student_id': student_id}).fetchone()

        return StudentProfileSummary(
            student_id=student_result[0],
            student_name=student_result[1],
            total_knowledge_points=stats_result[0] or 0,
            mastered_count=stats_result[1] or 0,
            learning_count=stats_result[2] or 0,
            weak_count=stats_result[3] or 0,
            latest_report_date=report_result[0] if report_result else None
        )

    except Exception as e:
        log.error(f"Error fetching student profile summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/{student_id}/knowledge-points")
async def get_student_knowledge_points(
    student_id: str,
    subject: Optional[str] = None,
    mastery_level_min: Optional[float] = None,
    mastery_level_max: Optional[float] = None,
    user: Users = Depends(get_current_user)
):
    """
    获取学生的知识点掌握情况

    参数:
    - subject: 筛选科目
    - mastery_level_min: 最小掌握度
    - mastery_level_max: 最大掌握度
    """
    # 权限检查
    if user.role not in ['admin', 'leader', 'teacher']:
        if user.id != student_id:
            raise HTTPException(status_code=403, detail="Permission denied")

    session = next(get_db())

    try:
        # 构建查询
        query = """
            SELECT
                id, student_id, subject, knowledge_point,
                total_attempts, correct_attempts, mastery_level,
                recent_trend, first_encountered, last_practiced,
                updated_at
            FROM student_knowledge_profile
            WHERE student_id = :student_id
        """
        params = {'student_id': student_id}

        if subject:
            query += " AND subject = :subject"
            params['subject'] = subject

        if mastery_level_min is not None:
            query += " AND mastery_level >= :min_mastery"
            params['min_mastery'] = mastery_level_min

        if mastery_level_max is not None:
            query += " AND mastery_level <= :max_mastery"
            params['max_mastery'] = mastery_level_max

        query += " ORDER BY subject, mastery_level DESC"

        result = session.execute(text(query), params)

        knowledge_points = []
        for row in result.fetchall():
            knowledge_points.append(KnowledgePointProfile(
                id=row[0],
                student_id=row[1],
                subject=row[2],
                knowledge_point=row[3],
                total_attempts=row[4],
                correct_attempts=row[5],
                mastery_level=row[6],
                recent_trend=row[7],
                first_encountered=row[8],
                last_practiced=row[9],
                updated_at=row[10]
            ))

        return knowledge_points

    except Exception as e:
        log.error(f"Error fetching knowledge points: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/{student_id}/reports")
async def get_student_reports(
    student_id: str,
    report_type: Optional[str] = None,
    limit: int = 10,
    user: Users = Depends(get_current_user)
):
    """
    获取学生的学习报告

    参数:
    - report_type: 报告类型 (daily/weekly/monthly)
    - limit: 返回数量
    """
    # 权限检查
    if user.role not in ['admin', 'leader', 'teacher']:
        if user.id != student_id:
            raise HTTPException(status_code=403, detail="Permission denied")

    session = next(get_db())

    try:
        query = """
            SELECT
                id, student_id, report_type, subject,
                period_start, period_end, summary,
                strengths, weaknesses, recommendations,
                generated_by, generated_at
            FROM learning_reports
            WHERE student_id = :student_id
        """
        params = {'student_id': student_id, 'limit': limit}

        if report_type:
            query += " AND report_type = :report_type"
            params['report_type'] = report_type

        query += " ORDER BY period_end DESC LIMIT :limit"

        result = session.execute(text(query), params)

        reports = []
        for row in result.fetchall():
            reports.append(LearningReport(
                id=row[0],
                student_id=row[1],
                report_type=row[2],
                subject=row[3],
                period_start=row[4],
                period_end=row[5],
                summary=row[6],
                strengths=row[7],
                weaknesses=row[8],
                recommendations=row[9],
                generated_by=row[10],
                generated_at=row[11]
            ))

        return reports

    except Exception as e:
        log.error(f"Error fetching learning reports: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students/{student_id}/weak-points")
async def get_student_weak_points(
    student_id: str,
    threshold: float = 0.5,
    user: Users = Depends(get_current_user)
):
    """
    获取学生的薄弱知识点(掌握度低于阈值)

    参数:
    - threshold: 掌握度阈值,默认0.5
    """
    # 权限检查
    if user.role not in ['admin', 'leader', 'teacher']:
        if user.id != student_id:
            raise HTTPException(status_code=403, detail="Permission denied")

    session = next(get_db())

    try:
        query = text("""
            SELECT
                id, student_id, subject, knowledge_point,
                total_attempts, correct_attempts, mastery_level,
                recent_trend, first_encountered, last_practiced,
                updated_at
            FROM student_knowledge_profile
            WHERE student_id = :student_id
              AND mastery_level < :threshold
            ORDER BY mastery_level ASC, total_attempts DESC
        """)

        result = session.execute(query, {
            'student_id': student_id,
            'threshold': threshold
        })

        weak_points = []
        for row in result.fetchall():
            weak_points.append(KnowledgePointProfile(
                id=row[0],
                student_id=row[1],
                subject=row[2],
                knowledge_point=row[3],
                total_attempts=row[4],
                correct_attempts=row[5],
                mastery_level=row[6],
                recent_trend=row[7],
                first_encountered=row[8],
                last_practiced=row[9],
                updated_at=row[10]
            ))

        return weak_points

    except Exception as e:
        log.error(f"Error fetching weak points: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/students")
async def get_all_students_summary(
    user: Users = Depends(get_current_user)
):
    """
    获取所有学生的画像摘要(仅教师/管理员)
    """
    if user.role not in ['admin', 'leader', 'teacher']:
        raise HTTPException(status_code=403, detail="Permission denied")

    session = next(get_db())

    try:
        query = text("""
            SELECT
                u.id,
                u.name,
                COUNT(DISTINCT skp.knowledge_point) as total_kp,
                SUM(CASE WHEN skp.mastery_level >= 0.8 THEN 1 ELSE 0 END) as mastered,
                SUM(CASE WHEN skp.mastery_level >= 0.5 AND skp.mastery_level < 0.8 THEN 1 ELSE 0 END) as learning,
                SUM(CASE WHEN skp.mastery_level < 0.5 THEN 1 ELSE 0 END) as weak,
                MAX(lr.period_end) as latest_report
            FROM user u
            LEFT JOIN student_knowledge_profile skp ON u.id = skp.student_id
            LEFT JOIN learning_reports lr ON u.id = lr.student_id
            WHERE u.role = 'student'
            GROUP BY u.id, u.name
            ORDER BY u.name
        """)

        result = session.execute(query)

        summaries = []
        for row in result.fetchall():
            summaries.append(StudentProfileSummary(
                student_id=row[0],
                student_name=row[1],
                total_knowledge_points=row[2] or 0,
                mastered_count=row[3] or 0,
                learning_count=row[4] or 0,
                weak_count=row[5] or 0,
                latest_report_date=row[6]
            ))

        return summaries

    except Exception as e:
        log.error(f"Error fetching all students summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
