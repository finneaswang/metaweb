# open_webui/metaweb/models/mistake.py
# Mistake tracking data models

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    """Difficulty level"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class MistakeType(str, Enum):
    """Mistake type"""
    CALCULATION = "calculation"
    CONCEPT = "concept"
    METHOD = "method"
    CARELESS = "careless"
    UNKNOWN = "unknown"


class KnowledgePoint(BaseModel):
    """Knowledge point"""
    id: str
    name: str
    chapter: Optional[str] = None
    mastery_level: float = Field(0.0, ge=0.0, le=1.0, description="Mastery level 0-1")


class MistakeCreate(BaseModel):
    """Create mistake record"""
    submission_id: str
    question_number: int
    question_content: Optional[str] = None
    student_answer: str
    correct_answer: str
    mistake_type: MistakeType = MistakeType.UNKNOWN
    knowledge_points: List[str] = Field(default_factory=list)
    ai_analysis: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None


class MistakeResponse(BaseModel):
    """Mistake record response"""
    id: str
    submission_id: str
    assignment_id: str
    student_id: str
    
    question_number: int
    question_content: Optional[str]
    student_answer: str
    correct_answer: str
    
    mistake_type: str
    knowledge_points: List[Dict]
    ai_analysis: Optional[str]
    ai_suggestions: Optional[str]
    difficulty: Optional[str]
    
    is_corrected: bool
    corrected_at: Optional[datetime]
    review_count: int
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class LearningReport(BaseModel):
    """Learning report"""
    student_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    
    total_assignments: int
    completed_assignments: int
    average_score: float
    total_mistakes: int
    corrected_mistakes: int
    
    weak_points: List[Dict]
    strong_points: List[Dict]
    
    progress_analysis: Optional[str]
    study_suggestions: Optional[str]
    
    generated_at: datetime


class StudentProfile(BaseModel):
    """Student knowledge profile"""
    student_id: str
    subject: str
    grade_level: str
    
    knowledge_mastery: Dict[str, float]
    
    calculation_ability: float = Field(0.0, ge=0.0, le=1.0)
    logical_thinking: float = Field(0.0, ge=0.0, le=1.0)
    problem_solving: float = Field(0.0, ge=0.0, le=1.0)
    
    total_study_time: int = 0
    average_completion_time: Optional[int] = None
    submission_rate: float = Field(0.0, ge=0.0, le=1.0)
    
    last_updated: datetime
    
    class Config:
        from_attributes = True
