# open_webui/metaweb/services/db_service.py
# Database Operations Service

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseService:
    """SQLite Database Operations"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use OpenWebUI's database path
            backend_path = Path(__file__).parent.parent.parent.parent
            db_path = backend_path / 'data' / 'webui.db'

        self.db_path = str(db_path)
        logger.info(f"Database path: {self.db_path}")

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # Assignment operations
    def create_assignment(self, assignment_data: dict) -> Optional[str]:
        """Create new assignment"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO assignments (
                    id, teacher_id, title, description, subject, grade_level,
                    publish_date, due_date, allow_late_submission, late_penalty_percent,
                    total_points, grading_mode, grading_rubric,
                    target_type, target_ids, allow_student_view_others,
                    allow_comments, enable_ocr, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assignment_data['id'],
                assignment_data['teacher_id'],
                assignment_data['title'],
                assignment_data.get('description'),
                assignment_data['subject'],
                assignment_data.get('grade_level'),
                assignment_data.get('publish_date', datetime.now().isoformat()),
                assignment_data['due_date'],
                assignment_data.get('allow_late_submission', False),
                assignment_data.get('late_penalty_percent', 0),
                assignment_data['total_points'],
                assignment_data['grading_mode'],
                assignment_data.get('grading_rubric'),
                assignment_data.get('target_type', 'class'),
                json.dumps(assignment_data.get('target_ids', [])),
                assignment_data.get('allow_student_view_others', False),
                assignment_data.get('allow_comments', True),
                assignment_data.get('enable_ocr', False),
                assignment_data.get('status', 'draft'),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            logger.info(f"Assignment created: {assignment_data['id']}")
            return assignment_data['id']

        except Exception as e:
            logger.error(f"Error creating assignment: {e}")
            return None

    def get_assignment(self, assignment_id: str) -> Optional[Dict]:
        """Get assignment by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM assignments WHERE id = ?', (assignment_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Error getting assignment: {e}")
            return None

    def update_assignment(self, assignment_id: str, updates: dict) -> bool:
        """Update assignment"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Build dynamic update query
            set_clauses = []
            values = []

            for key, value in updates.items():
                if key in ['id', 'created_at']:
                    continue
                set_clauses.append(f"{key} = ?")
                values.append(value)

            set_clauses.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(assignment_id)

            query = f"UPDATE assignments SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)

            conn.commit()
            conn.close()

            logger.info(f"Assignment updated: {assignment_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating assignment: {e}")
            return False

    def list_assignments(
        self,
        teacher_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """List assignments with filters"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM assignments WHERE 1=1"
            params = []

            if teacher_id:
                query += " AND teacher_id = ?"
                params.append(teacher_id)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error listing assignments: {e}")
            return []

    # Submission operations
    def create_submission(self, submission_data: dict) -> Optional[str]:
        """Create new submission"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO submissions (
                    id, assignment_id, student_id, answer_type,
                    answer_files, answer_text, time_spent_seconds,
                    status, submitted_at, is_late
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                submission_data['id'],
                submission_data['assignment_id'],
                submission_data['student_id'],
                submission_data.get('answer_type', 'file'),
                json.dumps(submission_data.get('answer_files', [])),
                submission_data.get('answer_text'),
                submission_data.get('time_spent_seconds'),
                submission_data.get('status', 'submitted'),
                datetime.now().isoformat(),
                submission_data.get('is_late', False)
            ))

            conn.commit()
            conn.close()

            logger.info(f"Submission created: {submission_data['id']}")
            return submission_data['id']

        except Exception as e:
            logger.error(f"Error creating submission: {e}")
            return None

    def get_submission(self, submission_id: str) -> Optional[Dict]:
        """Get submission by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM submissions WHERE id = ?', (submission_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Error getting submission: {e}")
            return None

    def update_submission(self, submission_id: str, updates: dict) -> bool:
        """Update submission with grading results"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            set_clauses = []
            values = []

            for key, value in updates.items():
                if key in ['id', 'submitted_at']:
                    continue
                set_clauses.append(f"{key} = ?")
                values.append(value)

            values.append(submission_id)
            query = f"UPDATE submissions SET {', '.join(set_clauses)} WHERE id = ?"

            cursor.execute(query, values)
            conn.commit()
            conn.close()

            logger.info(f"Submission updated: {submission_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating submission: {e}")
            return False

    def list_submissions(
        self,
        assignment_id: Optional[str] = None,
        student_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """List submissions with filters"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM submissions WHERE 1=1"
            params = []

            if assignment_id:
                query += " AND assignment_id = ?"
                params.append(assignment_id)

            if student_id:
                query += " AND student_id = ?"
                params.append(student_id)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY submitted_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error listing submissions: {e}")
            return []

    # Mistake operations
    def create_mistake(self, mistake_data: dict) -> Optional[str]:
        """Record a mistake"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO mistake_records (
                    id, submission_id, assignment_id, student_id,
                    question_number, question_content, student_answer, correct_answer,
                    mistake_type, knowledge_points, ai_analysis, ai_suggestions,
                    difficulty, is_corrected, review_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                mistake_data['id'],
                mistake_data['submission_id'],
                mistake_data['assignment_id'],
                mistake_data['student_id'],
                mistake_data['question_number'],
                mistake_data.get('question_content'),
                mistake_data['student_answer'],
                mistake_data['correct_answer'],
                mistake_data.get('mistake_type', 'unknown'),
                json.dumps(mistake_data.get('knowledge_points', [])),
                mistake_data.get('ai_analysis'),
                mistake_data.get('ai_suggestions'),
                mistake_data.get('difficulty'),
                False,
                0,
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            logger.info(f"Mistake recorded: {mistake_data['id']}")
            return mistake_data['id']

        except Exception as e:
            logger.error(f"Error creating mistake: {e}")
            return None

    def get_student_mistakes(
        self,
        student_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get student's mistake history"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM mistake_records
                WHERE student_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (student_id, limit))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting student mistakes: {e}")
            return []


# Global instance
db_service = None  # Initialize when needed
