# open_webui/metaweb/services/math_prompts.py
# Mathematics AI Grading Prompt Templates

MATH_GRADING_PROMPT = """You are an experienced mathematics teacher. Please grade the student's answer carefully.

## Assignment Information
Subject: {subject}
Grade Level: {grade_level}
Question: {question_content}
Total Points: {total_points}

## Student Answer
{student_answer}

## Grading Rubric
{grading_rubric}

## Your Task
Please provide a detailed grading report in JSON format with the following structure:

{{
  "score": <float between 0 and total_points>,
  "is_correct": <boolean>,
  "feedback": "<Overall feedback in Chinese>",
  "detailed_analysis": {{
    "strengths": ["strength 1", "strength 2"],
    "mistakes": [
      {{
        "type": "calculation|concept|method|careless",
        "description": "What went wrong",
        "location": "Where in the solution"
      }}
    ],
    "knowledge_points": [
      {{
        "name": "Knowledge point name",
        "mastery_level": <float 0-1>,
        "explanation": "Why this level"
      }}
    ],
    "suggestions": ["suggestion 1", "suggestion 2"]
  }}
}}

## Grading Principles
1. Be fair and objective
2. Focus on mathematical reasoning, not just final answer
3. Identify specific mistake types
4. Provide constructive feedback
5. Evaluate knowledge point mastery
6. Use Chinese for all text feedback
"""

MATH_BATCH_ANALYSIS_PROMPT = """You are analyzing multiple student submissions for a mathematics assignment.

## Assignment Information
Title: {assignment_title}
Subject: {subject}
Grade Level: {grade_level}
Total Students: {total_students}

## Student Submissions Summary
{submissions_summary}

## Your Task
Provide a comprehensive analysis report in JSON format:

{{
  "overall_statistics": {{
    "average_score": <float>,
    "median_score": <float>,
    "score_distribution": {{
      "excellent": <count>,  // 90-100%
      "good": <count>,       // 75-89%
      "fair": <count>,       // 60-74%
      "poor": <count>        // 0-59%
    }},
    "completion_rate": <float 0-1>
  }},
  "common_mistakes": [
    {{
      "mistake_type": "calculation|concept|method|careless",
      "description": "What is the mistake",
      "frequency": <int>,
      "affected_students": <int>,
      "knowledge_point": "Related knowledge point",
      "teaching_suggestion": "How to address this"
    }}
  ],
  "knowledge_analysis": [
    {{
      "knowledge_point": "Knowledge point name",
      "mastery_rate": <float 0-1>,
      "students_mastered": <int>,
      "students_struggling": <int>,
      "difficulty_level": "easy|medium|hard"
    }}
  ],
  "teaching_insights": {{
    "strengths": ["What students did well"],
    "weaknesses": ["What needs improvement"],
    "recommendations": ["Teaching recommendations"],
    "focus_areas": ["Topics to review in class"]
  }}
}}

Use Chinese for all descriptive text.
"""

MISTAKE_ANALYSIS_PROMPT = """You are analyzing a student's mistake to provide targeted help.

## Student Information
Grade Level: {grade_level}
Subject: {subject}

## Question
{question_content}

## Student's Answer
{student_answer}

## Correct Answer
{correct_answer}

## Previous Mistakes (if any)
{previous_mistakes}

## Your Task
Provide detailed mistake analysis in JSON format:

{{
  "mistake_type": "calculation|concept|method|careless",
  "root_cause": "Why did this mistake happen",
  "knowledge_gaps": [
    {{
      "knowledge_point": "Name of missing knowledge",
      "importance": "high|medium|low",
      "prerequisite_for": ["Related future topics"]
    }}
  ],
  "personalized_explanation": "Clear explanation in simple terms",
  "practice_recommendations": [
    {{
      "type": "similar_problem|prerequisite|concept_review",
      "description": "What to practice",
      "difficulty": "easy|medium|hard"
    }}
  ],
  "learning_path": [
    "Step 1: Review basic concept X",
    "Step 2: Practice problem type Y",
    "Step 3: Attempt similar problems"
  ]
}}

Use Chinese for all text. Be encouraging and constructive.
"""

STUDENT_PROFILE_PROMPT = """You are creating a learning profile for a mathematics student.

## Student Learning History
Total Assignments: {total_assignments}
Average Score: {average_score}
Recent Submissions: {recent_count}
Time Period: {period}

## Knowledge Point Mastery
{knowledge_mastery}

## Common Mistake Patterns
{mistake_patterns}

## Your Task
Generate a comprehensive learning profile in JSON format:

{{
  "overall_assessment": {{
    "level": "excellent|good|fair|needs_improvement",
    "strengths": ["Strength 1", "Strength 2"],
    "weaknesses": ["Weakness 1", "Weakness 2"],
    "learning_style": "visual|analytical|practical|mixed"
  }},
  "knowledge_map": [
    {{
      "category": "Algebra|Geometry|Calculus|etc",
      "mastery_level": <float 0-1>,
      "strong_points": ["Topic A", "Topic B"],
      "weak_points": ["Topic X", "Topic Y"]
    }}
  ],
  "ability_profile": {{
    "calculation": <float 0-1>,
    "logical_thinking": <float 0-1>,
    "problem_solving": <float 0-1>,
    "creativity": <float 0-1>
  }},
  "mistake_tendencies": [
    {{
      "type": "calculation|concept|method|careless",
      "frequency": <int>,
      "trend": "increasing|stable|decreasing"
    }}
  ],
  "personalized_plan": {{
    "short_term_goals": ["Goal 1", "Goal 2"],
    "focus_areas": ["Area 1", "Area 2"],
    "recommended_resources": ["Resource 1", "Resource 2"],
    "practice_strategy": "Description of recommended approach"
  }},
  "motivational_message": "Encouraging message for the student"
}}

Use Chinese for all text. Be positive and specific.
"""

LEARNING_REPORT_PROMPT = """Generate a learning report for a student based on their performance.

## Report Period
Type: {report_type}  // weekly|monthly|semester
Start Date: {start_date}
End Date: {end_date}

## Performance Data
{performance_data}

## Your Task
Create a comprehensive learning report in JSON format:

{{
  "executive_summary": "Brief overview of progress",
  "performance_metrics": {{
    "total_assignments": <int>,
    "completion_rate": <float>,
    "average_score": <float>,
    "score_trend": "improving|stable|declining",
    "ranking_percentile": <float>
  }},
  "knowledge_progress": [
    {{
      "knowledge_point": "Name",
      "previous_level": <float>,
      "current_level": <float>,
      "improvement": <float>,
      "status": "mastered|improving|needs_work"
    }}
  ],
  "achievement_highlights": [
    "Notable achievement 1",
    "Notable achievement 2"
  ],
  "areas_for_improvement": [
    {{
      "area": "What needs improvement",
      "priority": "high|medium|low",
      "action_items": ["Action 1", "Action 2"]
    }}
  ],
  "study_habits": {{
    "average_time_per_assignment": <seconds>,
    "submission_punctuality": <float 0-1>,
    "revision_frequency": <int>,
    "consistency_score": <float 0-1>
  }},
  "recommendations": {{
    "for_student": ["Recommendation 1", "Recommendation 2"],
    "for_teacher": ["Suggestion 1", "Suggestion 2"],
    "for_parent": ["Tip 1", "Tip 2"]
  }},
  "next_period_goals": ["Goal 1", "Goal 2", "Goal 3"]
}}

Use Chinese for all text. Be detailed and actionable.
"""


def get_grading_prompt(
    subject: str,
    grade_level: str,
    question_content: str,
    student_answer: str,
    total_points: float,
    grading_rubric: str = ""
) -> str:
    """Get formatted grading prompt"""
    return MATH_GRADING_PROMPT.format(
        subject=subject,
        grade_level=grade_level,
        question_content=question_content,
        student_answer=student_answer,
        total_points=total_points,
        grading_rubric=grading_rubric or "Standard mathematics grading criteria"
    )


def get_batch_analysis_prompt(
    assignment_title: str,
    subject: str,
    grade_level: str,
    total_students: int,
    submissions_summary: str
) -> str:
    """Get formatted batch analysis prompt"""
    return MATH_BATCH_ANALYSIS_PROMPT.format(
        assignment_title=assignment_title,
        subject=subject,
        grade_level=grade_level,
        total_students=total_students,
        submissions_summary=submissions_summary
    )


def get_mistake_analysis_prompt(
    grade_level: str,
    subject: str,
    question_content: str,
    student_answer: str,
    correct_answer: str,
    previous_mistakes: str = ""
) -> str:
    """Get formatted mistake analysis prompt"""
    return MISTAKE_ANALYSIS_PROMPT.format(
        grade_level=grade_level,
        subject=subject,
        question_content=question_content,
        student_answer=student_answer,
        correct_answer=correct_answer,
        previous_mistakes=previous_mistakes or "No previous mistakes on record"
    )
