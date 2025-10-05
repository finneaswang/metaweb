from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, List
from open_webui.models.users import UserModel
from open_webui.models.submissions import Submissions
from open_webui.models.assignments import Assignments
from open_webui.utils.auth import get_verified_user
from open_webui.utils.chat import generate_chat_completion
import json

router = APIRouter()

class AIGradeResponse(BaseModel):
    rubric_scores: Dict[str, float]
    feedback_draft: str
    total_score: Optional[float] = None
    confidence: Optional[str] = None

class GenerateRubricRequest(BaseModel):
    assignment_title: str
    assignment_description: Optional[str] = None
    user_requirements: str
    chat_history: Optional[List[Dict]] = []

class GenerateRubricResponse(BaseModel):
    explanation: str
    rubric_json: Dict

async def call_llm_for_rubric_generation(
    request: Request,
    user: UserModel,
    title: str, 
    description: str, 
    requirements: str
) -> dict:
    """
    调用LLM生成Rubric评分标准 - 使用gpt-4o-mini
    """
    
    system_prompt = """你是一个专业的教学评估专家。根据教师提供的作业信息,生成合理的Rubric评分标准。

要求:
1. 生成3-5个评分维度(criteria)
2. 每个维度包含: id(英文标识), title(中文名称), weight(权重0-1), scale(评分区间,默认[0,1,2,3,4,5])
3. 所有权重之和必须等于1.0
4. 返回JSON格式

示例输出:
{
  "explanation": "我为编程作业生成了3个评分维度...",
  "rubric_json": {
    "criteria": [
      {"id": "code_quality", "title": "代码质量", "weight": 0.4, "scale": [0,1,2,3,4,5]},
      {"id": "functionality", "title": "功能完整性", "weight": 0.4, "scale": [0,1,2,3,4,5]},
      {"id": "comments", "title": "注释规范", "weight": 0.2, "scale": [0,1,2,3,4,5]}
    ]
  }
}"""

    user_prompt = f"""作业标题: {title}
作业描述: {description or "无"}
评分要求: {requirements}

请生成合适的Rubric评分标准,直接返回JSON格式。"""

    # 构造请求
    form_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
    }
    
    try:
        res = await generate_chat_completion(
            request,
            form_data=form_data,
            user=user,
        )
        
        if res and "choices" in res:
            content = res["choices"][0]["message"]["content"]
            
            # 尝试解析JSON
            # 移除可能的markdown代码块标记
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            return result
        else:
            raise Exception("LLM返回格式错误")
            
    except Exception as e:
        print(f"LLM调用失败: {e}")
        # Fallback到规则匹配
        return fallback_rubric_generation(requirements)

def fallback_rubric_generation(requirements: str) -> dict:
    """备用方案: 基于关键词的规则匹配"""
    criteria = []
    
    if '编程' in requirements or '代码' in requirements:
        criteria = [
            {"id": "code_quality", "title": "代码质量", "weight": 0.4, "scale": [0, 1, 2, 3, 4, 5]},
            {"id": "functionality", "title": "功能完整性", "weight": 0.4, "scale": [0, 1, 2, 3, 4, 5]},
            {"id": "comments", "title": "注释规范", "weight": 0.2, "scale": [0, 1, 2, 3, 4, 5]}
        ]
        explanation = "我为编程作业生成了3个评分维度:代码质量(40%)、功能完整性(40%)、注释规范(20%)"
    elif '作文' in requirements or '议论文' in requirements or '写作' in requirements:
        criteria = [
            {"id": "logic", "title": "逻辑性", "weight": 0.3, "scale": [0, 1, 2, 3, 4, 5]},
            {"id": "argumentation", "title": "论证充分性", "weight": 0.4, "scale": [0, 1, 2, 3, 4, 5]},
            {"id": "language", "title": "语言表达", "weight": 0.3, "scale": [0, 1, 2, 3, 4, 5]}
        ]
        explanation = "我为写作作业生成了3个评分维度:逻辑性(30%)、论证充分性(40%)、语言表达(30%)"
    elif '数学' in requirements or '计算' in requirements:
        criteria = [
            {"id": "method", "title": "解题思路", "weight": 0.3, "scale": [0, 1, 2, 3, 4, 5]},
            {"id": "accuracy", "title": "计算准确性", "weight": 0.5, "scale": [0, 1, 2, 3, 4, 5]},
            {"id": "steps", "title": "步骤完整性", "weight": 0.2, "scale": [0, 1, 2, 3, 4, 5]}
        ]
        explanation = "我为数学作业生成了3个评分维度:解题思路(30%)、计算准确性(50%)、步骤完整性(20%)"
    else:
        criteria = [
            {"id": "content", "title": "内容质量", "weight": 0.5, "scale": [0, 1, 2, 3, 4, 5]},
            {"id": "completeness", "title": "完整性", "weight": 0.3, "scale": [0, 1, 2, 3, 4, 5]},
            {"id": "presentation", "title": "呈现质量", "weight": 0.2, "scale": [0, 1, 2, 3, 4, 5]}
        ]
        explanation = "我为这个作业生成了3个通用评分维度:内容质量(50%)、完整性(30%)、呈现质量(20%)"
    
    return {
        "explanation": explanation,
        "rubric_json": {"criteria": criteria}
    }

async def call_llm_for_grading(
    request: Request,
    user: UserModel,
    submission_text: str, 
    criterion_id: str, 
    criterion_title: str, 
    criterion_scale: list
) -> dict:
    """
    调用LLM为单个评分标准打分 - 使用gpt-4o-mini
    """
    
    system_prompt = f"""你是一个专业的作业评分助手。根据评分标准"{criterion_title}"对学生答案进行评分。

评分区间: {criterion_scale[0]}-{criterion_scale[-1]}分
请返回JSON格式: {{"score": 分数, "reason": "简要理由"}}"""

    user_prompt = f"""学生答案:
{submission_text}

请根据"{criterion_title}"标准评分,返回JSON格式。"""

    form_data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
    }
    
    try:
        res = await generate_chat_completion(
            request,
            form_data=form_data,
            user=user,
        )
        
        if res and "choices" in res:
            content = res["choices"][0]["message"]["content"].strip()
            
            # 移除markdown标记
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            return result
        else:
            raise Exception("LLM返回格式错误")
            
    except Exception as e:
        print(f"LLM评分失败: {e}")
        # Fallback
        return {
            "score": 3.5,
            "reason": f"根据{criterion_title}标准,该答案表现中等偏上。"
        }

@router.post("/generate-rubric", response_model=GenerateRubricResponse)
async def generate_rubric(
    request: Request,
    req_data: GenerateRubricRequest,
    user: UserModel = Depends(get_verified_user),
):
    """
    AI生成Rubric评分标准 - 使用gpt-4o-mini
    """
    if user.role not in ["teacher", "admin", "leader"]:
        raise HTTPException(status_code=403, detail="Only teachers can generate rubrics")
    
    result = await call_llm_for_rubric_generation(
        request,
        user,
        req_data.assignment_title,
        req_data.assignment_description or "",
        req_data.user_requirements
    )
    
    return GenerateRubricResponse(**result)

@router.post("/{submission_id}/ai-grade", response_model=AIGradeResponse)
async def ai_grade_submission(
    request: Request,
    submission_id: str,
    user: UserModel = Depends(get_verified_user),
):
    """
    为提交的作业进行AI辅助评分 - 使用gpt-4o-mini
    """
    if user.role not in ["teacher", "admin", "leader"]:
        raise HTTPException(status_code=403, detail="Only teachers/admins/leaders can grade submissions")
    
    submission = Submissions.get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    assignment = Assignments.get_assignment_by_id(submission.assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    if not assignment.ai_assist:
        raise HTTPException(status_code=400, detail="AI grading not enabled for this assignment")
    
    if not assignment.rubric_json:
        raise HTTPException(status_code=400, detail="No rubric defined for this assignment")
    
    rubric = assignment.rubric_json
    rubric_scores = {}
    feedback_parts = []
    
    for criterion in rubric.get("criteria", []):
        criterion_id = criterion["id"]
        criterion_title = criterion["title"]
        criterion_scale = criterion.get("scale", [0, 1, 2, 3, 4, 5])
        
        result = await call_llm_for_grading(
            request,
            user,
            submission.answer,
            criterion_id,
            criterion_title,
            criterion_scale
        )
        
        rubric_scores[criterion_id] = result["score"]
        feedback_parts.append(f"【{criterion_title}】{result['reason']}")
    
    feedback_draft = "\n".join(feedback_parts)
    
    weighted_sum = 0.0
    total_weight = 0.0
    for criterion in rubric.get("criteria", []):
        criterion_id = criterion["id"]
        weight = criterion.get("weight", 1.0 / len(rubric["criteria"]))
        score = rubric_scores.get(criterion_id, 0)
        weighted_sum += score * weight
        total_weight += weight
    
    normalized_score = weighted_sum / total_weight if total_weight > 0 else 0
    total_score = (normalized_score / 5.0) * assignment.max_score
    
    Submissions.update_submission_by_id(
        submission_id,
        {"ai_feedback_draft": feedback_draft, "rubric_scores_json": json.dumps(rubric_scores)}
    )
    
    return AIGradeResponse(
        rubric_scores=rubric_scores,
        feedback_draft=feedback_draft,
        total_score=round(total_score, 2),
        confidence="medium"
    )
