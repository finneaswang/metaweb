"""
PDC (Personal Data Center) API Router
Connects to separate PostgreSQL database for psychological data
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import json

from open_webui.utils.auth import get_verified_user

router = APIRouter()

# PostgreSQL connection config
PDC_DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "pdc_db",
    "user": "pdc_user",
    "password": "1234567890"
}


def get_db_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(**PDC_DB_CONFIG)


# ==================== Models ====================

class PsychologicalDataUpdate(BaseModel):
    weekly_chat_duration: Optional[int] = None
    last_chat_date: Optional[str] = None
    mood_summary: Optional[str] = None
    stress_level: Optional[int] = None
    sleep_quality: Optional[str] = None
    ai_suggestions: Optional[str] = None
    mental_health_indicators: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class SaveChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_duration: int


class ReportCreate(BaseModel):
    week_number: int
    year: int
    mood: str
    stress_level: int
    chat_duration: int
    summary: str
    suggestions: str


# ==================== Psychological Data ====================

@router.get("/psychological/data")
async def get_psychological_data(user=Depends(get_verified_user)):
    """Get user's psychological data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "SELECT * FROM psychological_data WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
            (user.id,)
        )
        result = cur.fetchone()

        cur.close()
        conn.close()

        if result:
            # Convert date objects to strings
            if result.get('last_chat_date'):
                result['last_chat_date'] = str(result['last_chat_date'])
            if result.get('created_at'):
                result['created_at'] = str(result['created_at'])
            if result.get('updated_at'):
                result['updated_at'] = str(result['updated_at'])
            return dict(result)

        return {
            "weekly_chat_duration": 0,
            "last_chat_date": None,
            "mood_summary": "",
            "stress_level": 0,
            "sleep_quality": "",
            "ai_suggestions": "",
            "mental_health_indicators": {
                "action_capability": 3,
                "self_worth_independence": 3,
                "exit_channel": 3,
                "stress_recovery": 3,
                "physical_state": 3,
                "social_connection": 3,
                "future_orientation": 3
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/psychological/data")
async def update_psychological_data(
    data: PsychologicalDataUpdate,
    user=Depends(get_verified_user)
):
    """Update user's psychological data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Check if record exists
        cur.execute(
            "SELECT id FROM psychological_data WHERE user_id = %s",
            (user.id,)
        )
        existing = cur.fetchone()

        if existing:
            # Update existing record
            update_fields = []
            values = []

            if data.weekly_chat_duration is not None:
                update_fields.append("weekly_chat_duration = %s")
                values.append(data.weekly_chat_duration)
            if data.last_chat_date is not None:
                update_fields.append("last_chat_date = %s")
                values.append(data.last_chat_date)
            if data.mood_summary is not None:
                update_fields.append("mood_summary = %s")
                values.append(data.mood_summary)
            if data.stress_level is not None:
                update_fields.append("stress_level = %s")
                values.append(data.stress_level)
            if data.sleep_quality is not None:
                update_fields.append("sleep_quality = %s")
                values.append(data.sleep_quality)
            if data.ai_suggestions is not None:
                update_fields.append("ai_suggestions = %s")
                values.append(data.ai_suggestions)
            if data.mental_health_indicators is not None:
                update_fields.append("mental_health_indicators = %s")
                values.append(Json(data.mental_health_indicators))

            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                values.append(user.id)

                cur.execute(
                    f"UPDATE psychological_data SET {', '.join(update_fields)} WHERE user_id = %s RETURNING *",
                    values
                )
        else:
            # Insert new record
            default_indicators = {
                "action_capability": 3,
                "self_worth_independence": 3,
                "exit_channel": 3,
                "stress_recovery": 3,
                "physical_state": 3,
                "social_connection": 3,
                "future_orientation": 3
            }
            indicators = data.mental_health_indicators if data.mental_health_indicators else default_indicators

            cur.execute(
                """INSERT INTO psychological_data
                   (user_id, weekly_chat_duration, last_chat_date, mood_summary, stress_level, sleep_quality, ai_suggestions, mental_health_indicators)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
                (
                    user.id,
                    data.weekly_chat_duration or 0,
                    data.last_chat_date,
                    data.mood_summary or "",
                    data.stress_level or 0,
                    data.sleep_quality or "",
                    data.ai_suggestions or "",
                    Json(indicators)
                )
            )

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result:
            if result.get('last_chat_date'):
                result['last_chat_date'] = str(result['last_chat_date'])
            if result.get('created_at'):
                result['created_at'] = str(result['created_at'])
            if result.get('updated_at'):
                result['updated_at'] = str(result['updated_at'])
            return dict(result)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Chat History ====================

@router.get("/psychological/chats")
async def get_psychological_chats(user=Depends(get_verified_user)):
    """Get user's psychological chat history"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "SELECT * FROM psychological_chats WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
            (user.id,)
        )
        results = cur.fetchall()

        cur.close()
        conn.close()

        for r in results:
            if r.get('created_at'):
                r['created_at'] = str(r['created_at'])

        return [dict(r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/psychological/chats")
async def save_psychological_chat(
    data: SaveChatRequest,
    user=Depends(get_verified_user)
):
    """Save a psychological chat session"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        messages_json = json.dumps([m.dict() for m in data.messages])

        cur.execute(
            """INSERT INTO psychological_chats (user_id, messages, session_duration)
               VALUES (%s, %s, %s) RETURNING *""",
            (user.id, messages_json, data.session_duration)
        )

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result and result.get('created_at'):
            result['created_at'] = str(result['created_at'])

        return dict(result) if result else result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Reports ====================

@router.get("/psychological/reports")
async def get_psychological_reports(user=Depends(get_verified_user)):
    """Get user's psychological reports"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            "SELECT * FROM psychological_reports WHERE user_id = %s ORDER BY created_at DESC",
            (user.id,)
        )
        results = cur.fetchall()

        cur.close()
        conn.close()

        for r in results:
            if r.get('created_at'):
                r['created_at'] = str(r['created_at'])

        return [dict(r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/psychological/reports")
async def create_psychological_report(
    data: ReportCreate,
    user=Depends(get_verified_user)
):
    """Create a psychological report"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """INSERT INTO psychological_reports
               (user_id, week_number, year, mood, stress_level, chat_duration, summary, suggestions)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (
                user.id,
                data.week_number,
                data.year,
                data.mood,
                data.stress_level,
                data.chat_duration,
                data.summary,
                data.suggestions
            )
        )

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if result and result.get('created_at'):
            result['created_at'] = str(result['created_at'])

        return dict(result) if result else result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Academic Radar Data ====================

class AcademicRadarData(BaseModel):
    academic_competitiveness: Optional[int] = None
    academic_resilience: Optional[int] = None
    academic_collaboration: Optional[int] = None
    active_learning: Optional[int] = None
    academic_capital: Optional[int] = None
    time_period: str = 'all'


@router.get("/academic/radar")
async def get_academic_radar_data(user=Depends(get_verified_user)):
    """Get user's academic radar data for all time and recent period"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get all-time data
        cur.execute(
            "SELECT * FROM academic_radar_data WHERE user_id = %s AND time_period = 'all' LIMIT 1",
            (user.id,)
        )
        all_time = cur.fetchone()

        # Get recent data (last month)
        cur.execute(
            "SELECT * FROM academic_radar_data WHERE user_id = %s AND time_period = 'recent' LIMIT 1",
            (user.id,)
        )
        recent = cur.fetchone()

        cur.close()
        conn.close()

        # Default values if no data exists
        default_data = {
            'academic_competitiveness': 50,
            'academic_resilience': 50,
            'academic_collaboration': 50,
            'active_learning': 50,
            'academic_capital': 50
        }

        return {
            'all_time': dict(all_time) if all_time else default_data,
            'recent': dict(recent) if recent else default_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/academic/radar")
async def update_academic_radar_data(
    data: AcademicRadarData,
    user=Depends(get_verified_user)
):
    """Update user's academic radar data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Check if record exists
        cur.execute(
            "SELECT id FROM academic_radar_data WHERE user_id = %s AND time_period = %s",
            (user.id, data.time_period)
        )
        existing = cur.fetchone()

        if existing:
            # Update existing record
            update_fields = []
            values = []

            if data.academic_competitiveness is not None:
                update_fields.append("academic_competitiveness = %s")
                values.append(data.academic_competitiveness)
            if data.academic_resilience is not None:
                update_fields.append("academic_resilience = %s")
                values.append(data.academic_resilience)
            if data.academic_collaboration is not None:
                update_fields.append("academic_collaboration = %s")
                values.append(data.academic_collaboration)
            if data.active_learning is not None:
                update_fields.append("active_learning = %s")
                values.append(data.active_learning)
            if data.academic_capital is not None:
                update_fields.append("academic_capital = %s")
                values.append(data.academic_capital)

            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                values.append(user.id)
                values.append(data.time_period)

                cur.execute(
                    f"UPDATE academic_radar_data SET {', '.join(update_fields)} WHERE user_id = %s AND time_period = %s RETURNING *",
                    values
                )
        else:
            # Insert new record
            cur.execute(
                """INSERT INTO academic_radar_data
                   (user_id, academic_competitiveness, academic_resilience, academic_collaboration, active_learning, academic_capital, time_period)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
                (
                    user.id,
                    data.academic_competitiveness or 50,
                    data.academic_resilience or 50,
                    data.academic_collaboration or 50,
                    data.active_learning or 50,
                    data.academic_capital or 50,
                    data.time_period
                )
            )

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return dict(result) if result else result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
