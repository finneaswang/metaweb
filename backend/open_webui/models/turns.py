import logging
import time
import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Index
from sqlalchemy import select

from open_webui.internal.db import Base, get_db

log = logging.getLogger(__name__)

####################
# Turns DB Schema
####################

class Turn(Base):
    __tablename__ = "turn"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text)
    tool_calls = Column(JSON, server_default="[]")  # 工具调用记录
    model = Column(String, nullable=True)  # 使用的模型
    tokens_in = Column(BigInteger, default=0)  # 输入tokens
    tokens_out = Column(BigInteger, default=0)  # 输出tokens
    cost = Column(BigInteger, default=0)  # 成本(微分)
    created_at = Column(BigInteger)
    meta = Column(JSON, server_default="{}")  # 其他元数据
    
    __table_args__ = (
        Index("turn_session_idx", "session_id"),
        Index("turn_created_idx", "created_at"),
    )

####################
# Turn Forms
####################

class TurnForm(BaseModel):
    session_id: str
    role: str
    content: str
    tool_calls: List[dict] = []
    model: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost: int = 0
    meta: dict = {}

class TurnModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    session_id: str
    role: str
    content: str
    tool_calls: List[dict]
    model: Optional[str] = None
    tokens_in: int
    tokens_out: int
    cost: int
    created_at: int
    meta: dict

####################
# TurnsTable
####################

class TurnsTable:
    def insert_new_turn(
        self, form_data: TurnForm
    ) -> Optional[TurnModel]:
        with get_db() as db:
            turn = TurnModel(
                **{
                    "id": str(uuid.uuid4()),
                    "session_id": form_data.session_id,
                    "role": form_data.role,
                    "content": form_data.content,
                    "tool_calls": form_data.tool_calls,
                    "model": form_data.model,
                    "tokens_in": form_data.tokens_in,
                    "tokens_out": form_data.tokens_out,
                    "cost": form_data.cost,
                    "created_at": int(time.time()),
                    "meta": form_data.meta,
                }
            )

            result = Turn(**turn.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return TurnModel.model_validate(result)

    def get_turn_by_id(self, id: str) -> Optional[TurnModel]:
        with get_db() as db:
            turn = db.query(Turn).filter_by(id=id).first()
            return TurnModel.model_validate(turn) if turn else None

    def get_turns_by_session_id(
        self, session_id: str, skip: int = 0, limit: int = 100
    ) -> List[TurnModel]:
        with get_db() as db:
            all_turns = (
                db.query(Turn)
                .filter_by(session_id=session_id)
                .order_by(Turn.created_at.asc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [TurnModel.model_validate(turn) for turn in all_turns]

    def get_turns_by_user_and_date(
        self, user_id: str, start_time: int, end_time: int
    ) -> List[TurnModel]:
        """获取某用户在指定时间范围内的所有turns（用于夜间分析）"""
        with get_db() as db:
            from open_webui.models.sessions import Session
            
            all_turns = (
                db.query(Turn)
                .join(Session, Turn.session_id == Session.id)
                .filter(Session.user_id == user_id)
                .filter(Turn.created_at >= start_time)
                .filter(Turn.created_at < end_time)
                .order_by(Turn.created_at.asc())
                .all()
            )
            return [TurnModel.model_validate(turn) for turn in all_turns]

    def delete_turn_by_id(self, id: str) -> bool:
        with get_db() as db:
            result = db.query(Turn).filter_by(id=id).delete()
            db.commit()
            return result > 0

Turns = TurnsTable()
