"""
LLM Proxy Router
统一代理所有LLM请求，记录sessions和turns用于画像分析
"""

import logging
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.models.sessions import Sessions, SessionForm
from open_webui.models.turns import Turns, TurnForm
from open_webui.models.users import Users
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()

####################
# 请求/响应模型
####################

class ProxyMessageRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None  # OpenWebUI的chat_id
    assignment_id: Optional[str] = None
    mode: str = "chat"  # chat, homework, deep_think
    model: Optional[str] = None
    meta: dict = {}

class ProxyMessageResponse(BaseModel):
    turn_id: str
    session_id: str
    content: str
    model: str
    meta: dict = {}

####################
# 核心路由
####################

@router.post("/proxy", response_model=ProxyMessageResponse)
async def llm_proxy(
    request: ProxyMessageRequest,
    user=Depends(get_verified_user),
):
    """
    LLM代理端点
    - 接收消息和元数据
    - 创建/获取session
    - 记录user turn
    - 调用实际LLM（这里先mock）
    - 记录assistant turn
    - 返回响应
    """
    
    try:
        # 1. 获取或创建session
        session_id = request.meta.get("session_id")
        
        if not session_id:
            # 创建新session
            session_form = SessionForm(
                user_id=user.id,
                assignment_id=request.assignment_id,
                mode=request.mode,
                policy_snapshot={
                    "model": request.model or "gpt-5",
                    "mode": request.mode,
                },
                meta={
                    "chat_id": request.chat_id,
                    **request.meta
                }
            )
            session = Sessions.insert_new_session(user.id, session_form)
            session_id = session.id
            log.info(f"Created new session: {session_id} for user {user.id}")
        else:
            session = Sessions.get_session_by_id(session_id)
            if not session or session.user_id != user.id:
                raise HTTPException(status_code=403, detail="Unauthorized session access")
        
        # 2. 记录用户消息 turn
        user_turn_form = TurnForm(
            session_id=session_id,
            role="user",
            content=request.message,
            meta=request.meta
        )
        user_turn = Turns.insert_new_turn(user_turn_form)
        log.info(f"Recorded user turn: {user_turn.id}")
        
        # 3. TODO: 调用实际LLM（这里先mock一个简单响应）
        # 根据mode选择不同的参数
        model_name = request.model or "gpt-5"
        max_tokens = 8000 if request.mode == "deep_think" else 2000
        
        # Mock 响应 - 实际应该调用 OpenAI API
        assistant_response = f"[Mock响应] 我理解了你的问题: {request.message[:50]}..."
        if request.assignment_id:
            assistant_response += f" (作业ID: {request.assignment_id})"
        
        # 4. 记录助手响应 turn
        assistant_turn_form = TurnForm(
            session_id=session_id,
            role="assistant",
            content=assistant_response,
            model=model_name,
            tokens_in=len(request.message),  # 简化计算
            tokens_out=len(assistant_response),
            cost=0,  # TODO: 实际计算成本
            meta={
                "max_tokens": max_tokens,
                "mode": request.mode,
            }
        )
        assistant_turn = Turns.insert_new_turn(assistant_turn_form)
        log.info(f"Recorded assistant turn: {assistant_turn.id}")
        
        # 5. 返回响应
        return ProxyMessageResponse(
            turn_id=assistant_turn.id,
            session_id=session_id,
            content=assistant_response,
            model=model_name,
            meta={
                "session_id": session_id,
                "mode": request.mode,
                "user_turn_id": user_turn.id,
            }
        )
        
    except Exception as e:
        log.error(f"Error in llm_proxy: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_user_sessions(
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
):
    """获取用户的所有sessions"""
    sessions = Sessions.get_sessions_by_user_id(user.id, skip=skip, limit=limit)
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/turns")
async def get_session_turns(
    session_id: str,
    user=Depends(get_verified_user),
):
    """获取某个session的所有turns"""
    session = Sessions.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    turns = Turns.get_turns_by_session_id(session_id)
    return {
        "session": session,
        "turns": turns
    }
