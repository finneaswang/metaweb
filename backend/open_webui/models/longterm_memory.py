import logging
import time
import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Index, ARRAY
from sqlalchemy import select

from open_webui.internal.db import Base, get_db

log = logging.getLogger(__name__)

####################
# Long-term Memory DB Schema
####################

class LongtermMemory(Base):
    __tablename__ = "longterm_memory"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    namespace = Column(String, nullable=False)  # profiles:user_id, skills:user_id
    tags = Column(JSON, server_default="[]")  # 标签数组
    text = Column(Text)  # 记忆内容
    metadata_json = Column(JSON, server_default="{}")  # 元数据
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    
    __table_args__ = (
        Index("longterm_memory_user_idx", "user_id"),
        Index("longterm_memory_namespace_idx", "namespace"),
        Index("longterm_memory_user_namespace_idx", "user_id", "namespace"),
    )

####################
# LongtermMemory Forms
####################

class LongtermMemoryForm(BaseModel):
    user_id: str
    namespace: str
    tags: List[str] = []
    text: str
    metadata_json: dict = {}

class LongtermMemoryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    namespace: str
    tags: List[str]
    text: str
    metadata_json: dict
    created_at: int
    updated_at: int

####################
# LongtermMemoriesTable
####################

class LongtermMemoriesTable:
    def insert_new_memory(
        self, form_data: LongtermMemoryForm
    ) -> Optional[LongtermMemoryModel]:
        with get_db() as db:
            memory = LongtermMemoryModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": form_data.user_id,
                    "namespace": form_data.namespace,
                    "tags": form_data.tags,
                    "text": form_data.text,
                    "metadata_json": form_data.metadata_json,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            result = LongtermMemory(**memory.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return LongtermMemoryModel.model_validate(result)

    def get_memories_by_user_and_namespace(
        self, user_id: str, namespace: str, skip: int = 0, limit: int = 50
    ) -> List[LongtermMemoryModel]:
        with get_db() as db:
            all_memories = (
                db.query(LongtermMemory)
                .filter_by(user_id=user_id, namespace=namespace)
                .order_by(LongtermMemory.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [LongtermMemoryModel.model_validate(mem) for mem in all_memories]

    def get_latest_profile(self, user_id: str) -> Optional[LongtermMemoryModel]:
        """获取用户最新的学习画像"""
        namespace = f"profiles:{user_id}"
        with get_db() as db:
            memory = (
                db.query(LongtermMemory)
                .filter_by(user_id=user_id, namespace=namespace)
                .order_by(LongtermMemory.updated_at.desc())
                .first()
            )
            return LongtermMemoryModel.model_validate(memory) if memory else None

    def search_memories_by_tags(
        self, user_id: str, tags: List[str], limit: int = 10
    ) -> List[LongtermMemoryModel]:
        """根据标签搜索记忆（简化版，实际应使用向量检索）"""
        with get_db() as db:
            # 简化实现：查询所有用户记忆，然后在Python中过滤
            all_memories = (
                db.query(LongtermMemory)
                .filter_by(user_id=user_id)
                .order_by(LongtermMemory.updated_at.desc())
                .limit(limit * 3)  # 取多一些再过滤
                .all()
            )
            
            # 过滤包含任一标签的记忆
            filtered = []
            for mem in all_memories:
                mem_tags = mem.tags if isinstance(mem.tags, list) else []
                if any(tag in mem_tags for tag in tags):
                    filtered.append(LongtermMemoryModel.model_validate(mem))
                    if len(filtered) >= limit:
                        break
            
            return filtered

    def update_memory_by_id(
        self, id: str, text: str, metadata_json: dict = None
    ) -> Optional[LongtermMemoryModel]:
        with get_db() as db:
            updates = {
                "text": text,
                "updated_at": int(time.time())
            }
            if metadata_json is not None:
                updates["metadata_json"] = metadata_json
            
            db.query(LongtermMemory).filter_by(id=id).update(updates)
            db.commit()
            
            memory = db.query(LongtermMemory).filter_by(id=id).first()
            return LongtermMemoryModel.model_validate(memory) if memory else None

    def delete_memory_by_id(self, id: str) -> bool:
        with get_db() as db:
            result = db.query(LongtermMemory).filter_by(id=id).delete()
            db.commit()
            return result > 0

LongtermMemories = LongtermMemoriesTable()
