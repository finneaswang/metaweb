from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from open_webui.models.assignments import Assignments
from open_webui.models.submissions import Submissions, SubmissionUpdateForm
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user
from open_webui.constants import ERROR_MESSAGES

import asyncio
import json

router = APIRouter()

############################
# AI Grading
############################


class AIGradeRequest(BaseModel):
    submission_id: str
    use_openai: Optional[bool] = True  # 使用哪个LLM提供商


class AIGradeResponse(BaseModel):
    rubric_scores: dict  # AI评分结果
    feedback_draft: str  # AI生成的评语
    total_score: float  # 总分
    confidence: float  # 置信度


async def call_llm_for_grading(
    assignment_content: str,
    student_answer: str,
    rubric: dict,
    criterion: dict
) -> dict:
    """
    调用LLM进行单项评分
    
    Args:
        assignment_content: 作业题目
        student_answer: 学生答案
        rubric: 完整rubric
        criterion: 当前评分项
    
    Returns:
        {
            "score": 3.5,
            "evidence": ["学生在...方面表现良好"],
            "feedback": "逻辑清晰，但..."
        }
    """
    # TODO: 实际调用LLM API
    # 这里先返回模拟数据
    
    prompt = f"""你是一位资深教师，正在批改作业。

作业题目：
{assignment_content}

学生答案：
{student_answer}

评分标准 - {criterion['title']}：
请根据以下标准评分（0-5分）：
- 5分：优秀
- 4分：良好  
- 3分：中等
- 2分：及格
- 1分：较差
- 0分：未作答或完全错误

请给出：
1. 分数（0-5）
2. 评分依据（引用学生答案中的具体内容）
3. 改进建议

以JSON格式返回：
{{
    "score": 数字,
    "evidence": ["依据1", "依据2"],
    "feedback": "具体反馈"
}}
"""
    
    # 模拟LLM响应
    await asyncio.sleep(0.5)  # 模拟API调用延迟
    
    # 简单的启发式评分（实际应该调用真正的LLM）
    score = 3.5
    if len(student_answer) > 100:
        score += 0.5
    if "例如" in student_answer or "比如" in student_answer:
        score += 0.5
        
    return {
        "score": min(5.0, score),
        "evidence": [
            f"学生在{criterion['title']}方面的表现",
            "答案内容较为充分"
        ],
        "feedback": f"在{criterion['title']}方面表现良好，建议进一步深化。"
    }


@router.post("/{submission_id}/ai-grade", response_model=AIGradeResponse)
async def ai_grade_submission(
    request: Request,
    submission_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """
    AI自动评分
    只有教师和管理员可以触发
    """
    # 验证权限
    if user.role not in ["teacher", "admin", "leader"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有教师和管理员可以使用AI评分"
        )
    
    # 获取提交
    submission = Submissions.get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="提交不存在"
        )
    
    # 获取作业
    assignment = Assignments.get_assignment_by_id(submission.assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="作业不存在"
        )
    
    # 检查是否有rubric
    if not assignment.rubric_json or not assignment.rubric_json.get("criteria"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该作业未设置评分标准"
        )
    
    # 检查是否启用AI
    if not assignment.ai_assist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该作业未启用AI辅助评分"
        )
    
    # 逐项评分
    rubric_scores = {}
    feedback_parts = []
    total_weighted_score = 0.0
    
    for criterion in assignment.rubric_json["criteria"]:
        result = await call_llm_for_grading(
            assignment_content=assignment.content or assignment.description,
            student_answer=submission.content or "",
            rubric=assignment.rubric_json,
            criterion=criterion
        )
        
        rubric_scores[criterion["id"]] = result["score"]
        feedback_parts.append(f"{criterion['title']}: {result['feedback']}")
        
        # 加权计算总分
        weight = criterion.get("weight", 1.0 / len(assignment.rubric_json["criteria"]))
        total_weighted_score += result["score"] * weight
    
    # 计算最终分数（0-5 scale转换到max_score）
    final_score = (total_weighted_score / 5.0) * assignment.max_score
    
    feedback_draft = "\n\n".join(feedback_parts)
    
    # 保存AI评分结果到submission
    update_form = SubmissionUpdateForm(
        ai_analysis=rubric_scores,
        ai_feedback_draft=feedback_draft,
        status="ai_reviewed"
    )
    Submissions.update_submission_by_id(submission_id, update_form)
    
    return AIGradeResponse(
        rubric_scores=rubric_scores,
        feedback_draft=feedback_draft,
        total_score=round(final_score, 2),
        confidence=0.85  # 模拟置信度
    )
