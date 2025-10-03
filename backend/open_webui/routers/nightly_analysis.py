"""
Nightly Analysis Router
夜间画像分析任务
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from open_webui.models.turns import Turns
from open_webui.models.sessions import Sessions
from open_webui.models.longterm_memory import LongtermMemories, LongtermMemoryForm
from open_webui.models.users import Users
from open_webui.utils.auth import get_verified_user, get_admin_user

log = logging.getLogger(__name__)

router = APIRouter()

####################
# 请求/响应模型
####################

class NightlyAnalysisRequest(BaseModel):
    user_id: str
    date: Optional[str] = None  # YYYY-MM-DD format, 默认为昨天

class ProfileAnalysisResult(BaseModel):
    user_id: str
    date: str
    total_turns: int
    summary: str
    weak_skills: List[str]
    strong_skills: List[str]
    evidence: List[dict]
    recommendations: List[str]
    profile_memory_id: Optional[str] = None

####################
# 核心函数
####################

def analyze_student_profile(user_id: str, turns: List[dict]) -> dict:
    """
    分析学生画像
    
    TODO: 实际应调用 GPT-5 进行分析
    这里先返回一个mock结果
    """
    
    # 统计信息
    total_messages = len([t for t in turns if t['role'] == 'user'])
    total_content = '\n'.join([t['content'] for t in turns])
    
    # Mock 画像结果
    profile = {
        "summary": f"学生今日共进行了{total_messages}轮对话，主要关注点在...",
        "weak_skills": ["数学推理", "代数运算"],
        "strong_skills": ["基础概念理解", "积极提问"],
        "evidence": [
            {
                "turn_id": turns[0]['id'] if turns else None,
                "skill": "数学推理",
                "evidence_text": "在解题时出现逻辑推理错误...",
                "timestamp": turns[0]['created_at'] if turns else None
            }
        ],
        "recommendations": [
            "建议加强数学推理练习",
            "可以尝试分步骤解题",
            "多做类似题型巩固"
        ],
        "metadata": {
            "total_turns": len(turns),
            "total_messages": total_messages,
            "analysis_timestamp": int(time.time()),
            "model": "gpt-5",  # 未来实际使用的模型
        }
    }
    
    return profile

####################
# 路由
####################

@router.post("/run", response_model=ProfileAnalysisResult)
async def run_nightly_analysis(
    request: NightlyAnalysisRequest,
    user=Depends(get_admin_user),  # 仅管理员可手动触发
):
    """
    手动触发夜间分析（用于测试）
    实际部署时应使用定时任务（cron/celery）
    """
    
    try:
        # 1. 确定分析日期
        if request.date:
            target_date = datetime.strptime(request.date, "%Y-%m-%d")
        else:
            target_date = datetime.now() - timedelta(days=1)  # 昨天
        
        # 计算时间范围（当天 00:00 到 23:59）
        start_time = int(target_date.replace(hour=0, minute=0, second=0).timestamp())
        end_time = int(target_date.replace(hour=23, minute=59, second=59).timestamp())
        
        log.info(f"Analyzing profile for user {request.user_id} on {target_date.strftime('%Y-%m-%d')}")
        
        # 2. 获取当天所有 turns
        turns = Turns.get_turns_by_user_and_date(request.user_id, start_time, end_time)
        
        if not turns:
            raise HTTPException(
                status_code=404,
                detail=f"No turns found for user {request.user_id} on {target_date.strftime('%Y-%m-%d')}"
            )
        
        # 转换为dict列表
        turns_data = [turn.model_dump() for turn in turns]
        
        # 3. 分析画像
        profile = analyze_student_profile(request.user_id, turns_data)
        
        # 4. 写入长期记忆
        memory_form = LongtermMemoryForm(
            user_id=request.user_id,
            namespace=f"profiles:{request.user_id}",
            tags=["daily_profile", target_date.strftime("%Y-%m-%d")] + profile['weak_skills'],
            text=json.dumps(profile, ensure_ascii=False),
            metadata_json={
                "date": target_date.strftime("%Y-%m-%d"),
                "total_turns": len(turns),
                "analysis_version": "v1.0",
            }
        )
        
        memory = LongtermMemories.insert_new_memory(memory_form)
        
        log.info(f"Profile memory created: {memory.id}")
        
        # 5. 返回结果
        return ProfileAnalysisResult(
            user_id=request.user_id,
            date=target_date.strftime("%Y-%m-%d"),
            total_turns=len(turns),
            summary=profile['summary'],
            weak_skills=profile['weak_skills'],
            strong_skills=profile['strong_skills'],
            evidence=profile['evidence'],
            recommendations=profile['recommendations'],
            profile_memory_id=memory.id
        )
        
    except Exception as e:
        log.error(f"Error in nightly analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/latest/{user_id}")
async def get_latest_profile(
    user_id: str,
    current_user=Depends(get_verified_user),
):
    """获取用户最新的学习画像"""
    
    # 权限检查：只能查看自己的画像或管理员
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    memory = LongtermMemories.get_latest_profile(user_id)
    
    if not memory:
        raise HTTPException(status_code=404, detail="No profile found")
    
    # 解析JSON
    profile_data = json.loads(memory.text)
    
    return {
        "memory_id": memory.id,
        "user_id": memory.user_id,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
        "profile": profile_data,
        "metadata": memory.metadata_json
    }


@router.get("/memories/{user_id}")
async def get_user_memories(
    user_id: str,
    namespace: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user=Depends(get_verified_user),
):
    """获取用户的记忆列表"""
    
    # 权限检查
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    if namespace:
        memories = LongtermMemories.get_memories_by_user_and_namespace(
            user_id, namespace, skip, limit
        )
    else:
        # 获取所有画像
        memories = LongtermMemories.get_memories_by_user_and_namespace(
            user_id, f"profiles:{user_id}", skip, limit
        )
    
    return {
        "user_id": user_id,
        "memories": memories,
        "total": len(memories)
    }
