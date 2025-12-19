from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from open_webui.internal.db import Base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AIConfig(Base):
    __tablename__ = 'user_ai_configs'
    
    user_id = Column(String, primary_key=True)
    api_provider = Column(String, default='openrouter')  # openrouter, anthropic, openai, etc.
    api_key = Column(Text)  # 加密存储
    api_base_url = Column(String, nullable=True)
    model_name = Column(String, default='anthropic/claude-3.5-sonnet')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AIConfigModel(BaseModel):
    user_id: str
    api_provider: str = 'openrouter'
    api_key: str
    api_base_url: Optional[str] = None
    model_name: str = 'anthropic/claude-3.5-sonnet'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AIConfigForm(BaseModel):
    api_provider: str = 'openrouter'
    api_key: str
    api_base_url: Optional[str] = None
    model_name: str = 'anthropic/claude-3.5-sonnet'
