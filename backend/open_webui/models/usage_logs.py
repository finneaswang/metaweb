import logging
import time
import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Float, JSON, Index
from sqlalchemy import select, func

from open_webui.internal.db import Base, get_db

log = logging.getLogger(__name__)

####################
# Usage Logs DB Schema
####################

class UsageLog(Base):
    __tablename__ = "usage_log"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    model = Column(String, nullable=False)  # 使用的模型
    mode = Column(String, default="chat")  # chat, homework, deep_think
    tokens_in = Column(BigInteger, default=0)
    tokens_out = Column(BigInteger, default=0)
    cost_usd = Column(Float, default=0.0)  # 成本（美元）
    session_id = Column(String, nullable=True)
    turn_id = Column(String, nullable=True)
    created_at = Column(BigInteger)
    metadata = Column(JSON, server_default="{}")
    
    __table_args__ = (
        Index("usage_log_user_idx", "user_id"),
        Index("usage_log_created_idx", "created_at"),
        Index("usage_log_user_created_idx", "user_id", "created_at"),
    )

####################
# UsageLog Forms
####################

class UsageLogForm(BaseModel):
    user_id: str
    model: str
    mode: str = "chat"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    metadata: dict = {}

class UsageLogModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    model: str
    mode: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    created_at: int
    metadata: dict

class UsageStatsModel(BaseModel):
    """用量统计模型"""
    total_requests: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    by_model: dict  # {"gpt-5": {"requests": 100, "tokens": 5000, "cost": 0.5}}
    by_mode: dict  # {"chat": {...}, "homework": {...}}

####################
# UsageLogsTable
####################

class UsageLogsTable:
    def insert_new_log(
        self, form_data: UsageLogForm
    ) -> Optional[UsageLogModel]:
        with get_db() as db:
            log_entry = UsageLogModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": form_data.user_id,
                    "model": form_data.model,
                    "mode": form_data.mode,
                    "tokens_in": form_data.tokens_in,
                    "tokens_out": form_data.tokens_out,
                    "cost_usd": form_data.cost_usd,
                    "session_id": form_data.session_id,
                    "turn_id": form_data.turn_id,
                    "created_at": int(time.time()),
                    "metadata": form_data.metadata,
                }
            )

            result = UsageLog(**log_entry.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return UsageLogModel.model_validate(result)

    def get_user_stats(
        self, user_id: str, start_time: int = None, end_time: int = None
    ) -> UsageStatsModel:
        """获取用户的用量统计"""
        with get_db() as db:
            query = db.query(UsageLog).filter_by(user_id=user_id)
            
            if start_time:
                query = query.filter(UsageLog.created_at >= start_time)
            if end_time:
                query = query.filter(UsageLog.created_at <= end_time)
            
            all_logs = query.all()
            
            # 统计
            total_requests = len(all_logs)
            total_tokens_in = sum(log.tokens_in for log in all_logs)
            total_tokens_out = sum(log.tokens_out for log in all_logs)
            total_cost_usd = sum(log.cost_usd for log in all_logs)
            
            # 按模型统计
            by_model = {}
            by_mode = {}
            
            for log in all_logs:
                # 按模型
                if log.model not in by_model:
                    by_model[log.model] = {
                        "requests": 0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "cost_usd": 0.0
                    }
                by_model[log.model]["requests"] += 1
                by_model[log.model]["tokens_in"] += log.tokens_in
                by_model[log.model]["tokens_out"] += log.tokens_out
                by_model[log.model]["cost_usd"] += log.cost_usd
                
                # 按模式
                if log.mode not in by_mode:
                    by_mode[log.mode] = {
                        "requests": 0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "cost_usd": 0.0
                    }
                by_mode[log.mode]["requests"] += 1
                by_mode[log.mode]["tokens_in"] += log.tokens_in
                by_mode[log.mode]["tokens_out"] += log.tokens_out
                by_mode[log.mode]["cost_usd"] += log.cost_usd
            
            return UsageStatsModel(
                total_requests=total_requests,
                total_tokens_in=total_tokens_in,
                total_tokens_out=total_tokens_out,
                total_cost_usd=total_cost_usd,
                by_model=by_model,
                by_mode=by_mode
            )

    def get_logs_by_user(
        self, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[UsageLogModel]:
        with get_db() as db:
            all_logs = (
                db.query(UsageLog)
                .filter_by(user_id=user_id)
                .order_by(UsageLog.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [UsageLogModel.model_validate(log) for log in all_logs]

UsageLogs = UsageLogsTable()
