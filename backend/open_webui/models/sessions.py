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
# Sessions DB Schema
####################

class Session(Base):
    __tablename__ = "session"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    assignment_id = Column(String, nullable=True)  # 关联作业ID
    mode = Column(String, default="chat")  # chat, homework, deep_think
    started_at = Column(BigInteger)
    ended_at = Column(BigInteger, nullable=True)
    policy_snapshot = Column(JSON, server_default="{}")  # 政策快照
    meta = Column(JSON, server_default="{}")  # 其他元数据
    
    __table_args__ = (
        Index("session_user_idx", "user_id"),
        Index("session_assignment_idx", "assignment_id"),
    )

####################
# Session Forms
####################

class SessionForm(BaseModel):
    user_id: str
    assignment_id: Optional[str] = None
    mode: str = "chat"
    policy_snapshot: dict = {}
    meta: dict = {}

class SessionModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    assignment_id: Optional[str] = None
    mode: str
    started_at: int
    ended_at: Optional[int] = None
    policy_snapshot: dict
    meta: dict

####################
# SessionsTable
####################

class SessionsTable:
    def insert_new_session(
        self, user_id: str, form_data: SessionForm
    ) -> Optional[SessionModel]:
        with get_db() as db:
            session = SessionModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "assignment_id": form_data.assignment_id,
                    "mode": form_data.mode,
                    "started_at": int(time.time()),
                    "policy_snapshot": form_data.policy_snapshot,
                    "meta": form_data.meta,
                }
            )

            result = Session(**session.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return SessionModel.model_validate(result)

    def get_session_by_id(self, id: str) -> Optional[SessionModel]:
        with get_db() as db:
            session = db.query(Session).filter_by(id=id).first()
            return SessionModel.model_validate(session) if session else None

    def get_sessions_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> List[SessionModel]:
        with get_db() as db:
            all_sessions = (
                db.query(Session)
                .filter_by(user_id=user_id)
                .order_by(Session.started_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [SessionModel.model_validate(session) for session in all_sessions]

    def update_session_by_id(
        self, id: str, updated: dict
    ) -> Optional[SessionModel]:
        with get_db() as db:
            db.query(Session).filter_by(id=id).update(updated)
            db.commit()
            
            session = db.query(Session).filter_by(id=id).first()
            return SessionModel.model_validate(session) if session else None

    def delete_session_by_id(self, id: str) -> bool:
        with get_db() as db:
            result = db.query(Session).filter_by(id=id).delete()
            db.commit()
            return result > 0

Sessions = SessionsTable()
