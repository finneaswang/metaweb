"""
AI长期记忆服务 - RAG实现
使用ChromaDB向量数据库 + 自动记忆提取
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class MemoryService:
    """AI记忆服务 - 类似ChatGPT的Memory功能"""
    
    def __init__(self, persist_directory="/home/linuxuser/openwebui-custom/data/memory_db"):
        """初始化向量数据库"""
        try:
            # 初始化 ChromaDB
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 获取或创建记忆集合
            self.collection = self.client.get_or_create_collection(
                name="user_memories",
                metadata={"description": "用户学习记忆和偏好"}
            )
            
            logger.info("Memory service initialized with ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}")
            raise
    
    async def extract_memories_from_conversation(
        self,
        user_message: str,
        ai_response: str,
        api_key: str,
        api_base_url: str = 'https://openrouter.ai/api/v1',
        model: str = "anthropic/claude-3.5-sonnet"
    ) -> List[str]:
        """从对话中提取值得记住的信息"""
        
        extraction_prompt = f"""分析以下对话，提取值得长期记住的关键信息。

规则：
1. 只提取重要的、可能在未来有用的信息
2. 包括：用户偏好、学习进度、困难点、目标、习惯等
3. 不包括：闲聊、临时问题、无关紧要的细节
4. 每条记忆用一句话概括
5. 如果没有值得记住的信息，返回空列表

对话：
用户: {user_message}
AI: {ai_response}

请以JSON格式返回记忆列表：
{{"memories": ["记忆1", "记忆2", ...]}}

只返回JSON，不要其他内容。"""

        try:
            import httpx
            
            url = f"{api_base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": extraction_prompt}],
                "max_tokens": 500,
                "temperature": 0.3
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 解析JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    return data.get('memories', [])
                return []
                
        except Exception as e:
            logger.error(f"Memory extraction error: {e}")
            return []
    
    def store_memory(
        self,
        user_id: str,
        memory_text: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """存储单条记忆到向量数据库"""
        try:
            memory_id = f"{user_id}_{datetime.now().timestamp()}"
            
            # 准备元数据
            meta = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                **(metadata or {})
            }
            
            # 添加到向量数据库
            self.collection.add(
                documents=[memory_text],
                metadatas=[meta],
                ids=[memory_id]
            )
            
            logger.info(f"Stored memory for user {user_id}: {memory_text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False
    
    def retrieve_memories(
        self,
        user_id: str,
        query: str,
        n_results: int = 5
    ) -> List[str]:
        """根据查询检索相关记忆"""
        try:
            # 向量检索
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"user_id": user_id}
            )
            
            if results and results['documents']:
                memories = results['documents'][0]  # 第一个查询的结果
                logger.info(f"Retrieved {len(memories)} memories for user {user_id}")
                return memories
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []
    
    def get_all_memories(self, user_id: str, limit: int = 20) -> List[Dict]:
        """获取用户所有记忆（用于管理界面）"""
        try:
            results = self.collection.get(
                where={"user_id": user_id},
                limit=limit
            )
            
            if results:
                memories = []
                for i, doc in enumerate(results.get('documents', [])):
                    memories.append({
                        'text': doc,
                        'metadata': results.get('metadatas', [])[i] if i < len(results.get('metadatas', [])) else {}
                    })
                return memories
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            return []
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除单条记忆"""
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    def clear_user_memories(self, user_id: str) -> bool:
        """清空用户所有记忆"""
        try:
            # ChromaDB 需要先查询再删除
            results = self.collection.get(where={"user_id": user_id})
            if results and results.get('ids'):
                self.collection.delete(ids=results['ids'])
            logger.info(f"Cleared all memories for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")
            return False


# 创建全局实例
memory_service = MemoryService()
