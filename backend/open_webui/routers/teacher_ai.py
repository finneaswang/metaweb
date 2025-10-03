from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from open_webui.models.users import Users
from open_webui.models.turns import Turns
from open_webui.models.submissions import Submissions
from open_webui.models.longterm_memory import LongtermMemories
from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
import time
from datetime import datetime, timedelta

router = APIRouter()

############################
# Request/Response Models
############################

class TeacherAIRequest(BaseModel):
    student_id: str
    question: str
    context: Optional[str] = None  # 额外上下文（如作业ID）

class DataSource(BaseModel):
    conversation_count: int
    assignment_count: int
    profile_date: Optional[int] = None
    date_range: str

class TeacherAIResponse(BaseModel):
    answer: str
    data_sources: DataSource
    student_name: str

############################
# Helper Functions
############################

def extract_topics(turns: List[Dict]) -> List[str]:
    """从对话中提取主要主题（简化版）"""
    topics = []
    for turn in turns:
        content = turn.get("content", "")
        # 简单的关键词提取
        if "数学" in content or "方程" in content:
            topics.append("数学")
        if "作业" in content:
            topics.append("作业")
        if "概念" in content or "定义" in content:
            topics.append("基础概念")
    return list(set(topics)) if topics else ["通用学习"]

def calculate_avg_score(submissions: List[Dict]) -> float:
    """计算平均分"""
    scores = [s.get("score", 0) for s in submissions if s.get("score") is not None]
    return round(sum(scores) / len(scores), 1) if scores else 0

def format_recent_submissions(submissions: List[Dict], limit: int = 3) -> str:
    """格式化最近的作业提交"""
    if not submissions:
        return "暂无作业记录"
    
    recent = sorted(submissions, key=lambda x: x.get("created_at", 0), reverse=True)[:limit]
    result = []
    for s in recent:
        score = s.get("score", "未批改")
        grade = s.get("grade", "")
        date = datetime.fromtimestamp(s.get("created_at", 0)).strftime("%Y-%m-%d")
        result.append(f"  - {date}: {score}分 ({grade})")
    return "\n".join(result)

async def call_gpt5_deep_think(system_prompt: str, user_message: str, mode: str = "deep_think") -> Dict[str, Any]:
    """
    调用 GPT-5 Deep Think 模式
    TODO: 实际接入 GPT-5 API
    """
    # Mock response for now
    mock_answer = f"""**学生学习情况分析**

根据收集到的数据分析：

**学习投入** ⭐⭐⭐⭐
- 最近 7 天活跃，参与了多次对话
- 作业完成情况良好

**知识掌握**
- ✅ 基础概念理解扎实
- ⚠️  部分知识点需要加强练习

**建议**
1. 继续保持当前的学习节奏
2. 针对薄弱环节进行专项训练
3. 适当增加实践练习

_此分析基于近期对话记录和作业表现生成_
"""
    
    return {
        "content": mock_answer,
        "model": "gpt-5-deep-think",
        "tokens": 500
    }

############################
# API Endpoints
############################

@router.post("/ask-ai", response_model=TeacherAIResponse)
async def ask_teacher_ai(
    request: TeacherAIRequest,
    user: UserModel = Depends(get_verified_user)
):
    """
    教师 AI 助手 - 回答关于学生的问题
    """
    # 1. 验证权限（必须是 teacher 或 admin）
    if user.role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有教师和管理员可以使用此功能"
        )
    
    # 2. 获取学生信息
    student = Users.get_user_by_id(request.student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="学生不存在"
        )
    
    # 3. 收集学生数据
    # 获取最近7天的对话
    now_ts = int(time.time())
    seven_days_ago = now_ts - (7 * 24 * 60 * 60)
    
    try:
        recent_turns = Turns.get_turns_by_user_and_date(
            request.student_id,
            start_time=seven_days_ago,
            end_time=now_ts
        )
    except Exception:
        recent_turns = []
    
    # 获取作业记录
    try:
        submissions = Submissions.get_submissions_by_student_id(request.student_id)
        submissions_data = [
            {
                "score": s.score,
                "grade": s.grade,
                "created_at": s.created_at,
                "status": s.status
            }
            for s in submissions
        ]
    except Exception:
        submissions_data = []
    
    # 获取最新学习画像
    try:
        profile = LongtermMemories.get_latest_profile(request.student_id)
        profile_text = profile.text if profile else "暂无 AI 学习画像"
        profile_date = profile.created_at if profile else None
    except Exception:
        profile_text = "暂无 AI 学习画像"
        profile_date = None
    
    # 4. 构建上下文
    turns_data = [{"content": t.content, "role": t.role} for t in recent_turns] if recent_turns else []
    topics = extract_topics(turns_data)
    avg_score = calculate_avg_score(submissions_data)
    recent_submissions_text = format_recent_submissions(submissions_data)
    
    last_active = datetime.fromtimestamp(student.last_active_at).strftime("%Y-%m-%d %H:%M") if student.last_active_at else "未知"
    
    context = f"""
学生信息：
- 姓名：{student.name}
- 邮箱：{student.email}
- 最后登录：{last_active}

最近学习画像（AI 夜间分析）：
{profile_text}

最近 7 天对话情况：
- 总对话轮数：{len(turns_data)}
- 主要讨论主题：{", ".join(topics)}

作业完成情况：
- 总作业数：{len(submissions_data)}
- 平均分：{avg_score}
- 最近 3 次作业：
{recent_submissions_text}
"""
    
    # 5. 调用 GPT-5 Deep Think
    system_prompt = """你是一位资深教学顾问 AI。
教师会向你询问学生的学习情况。
请基于提供的数据，给出专业、具体、可操作的分析。
必须引用具体数据支撑你的结论。
回答要结构化，使用 Markdown 格式。"""
    
    user_message = f"{context}\n\n教师的问题：{request.question}"
    
    response = await call_gpt5_deep_think(
        system_prompt=system_prompt,
        user_message=user_message,
        mode="deep_think"
    )
    
    # 6. 返回结果
    return TeacherAIResponse(
        answer=response["content"],
        student_name=student.name,
        data_sources=DataSource(
            conversation_count=len(turns_data),
            assignment_count=len(submissions_data),
            profile_date=profile_date,
            date_range="最近 7 天"
        )
    )

@router.get("/students", response_model=List[Dict[str, Any]])
async def get_teacher_students(
    user: UserModel = Depends(get_verified_user)
):
    """
    获取教师可见的学生列表
    """
    if user.role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有教师和管理员可以访问"
        )
    
    # 获取所有学生角色的用户
    all_users = Users.get_users()
    students = [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "last_active_at": u.last_active_at,
            "role": u.role
        }
        for u in all_users
        if u.role == "student"
    ]
    
    return students
