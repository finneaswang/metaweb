# Personal Data Center - 独立 PostgreSQL 数据库服务
# 完全独立，不影响 OpenWebUI

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class PersonalDataCenterDB:
    """Personal Data Center 独立 PostgreSQL 数据库"""

    def __init__(self):
        self.db_config = {
            'dbname': 'pdc_db',
            'user': 'pdc_user',
            'password': '1234567890',
            'host': 'localhost',
            'port': '5432'
        }
        logger.info("Personal Data Center PostgreSQL initialized")
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 创建 API 配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_api_configs (
                    user_id TEXT PRIMARY KEY,
                    api_provider TEXT NOT NULL DEFAULT 'openrouter',
                    api_key TEXT,
                    api_base_url TEXT,
                    model_name TEXT NOT NULL DEFAULT 'anthropic/claude-3.5-sonnet',
                    use_system_config BOOLEAN NOT NULL DEFAULT FALSE,
                    system_url_idx INTEGER,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # 兼容旧表结构：补字段 & 允许 api_key 为空（用于“使用系统配置”模式）
            cursor.execute('ALTER TABLE user_api_configs ADD COLUMN IF NOT EXISTS use_system_config BOOLEAN NOT NULL DEFAULT FALSE;')
            cursor.execute('ALTER TABLE user_api_configs ADD COLUMN IF NOT EXISTS system_url_idx INTEGER;')
            try:
                cursor.execute('ALTER TABLE user_api_configs ALTER COLUMN api_key DROP NOT NULL;')
            except Exception:
                # 部分版本/状态下可能已是可空，忽略
                pass

            # 创建对话历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    files JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 🆕 创建学生档案文件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profile_files (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    description TEXT,
                    category TEXT DEFAULT 'other',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_chat_user_created
                ON chat_history (user_id, created_at DESC)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_profile_files_user
                ON profile_files (user_id, created_at DESC)
            ''')

            # 创建更新时间触发器
            cursor.execute('''
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            ''')

            cursor.execute('''
                DROP TRIGGER IF EXISTS update_user_api_configs_updated_at ON user_api_configs;
            ''')

            cursor.execute('''
                CREATE TRIGGER update_user_api_configs_updated_at
                BEFORE UPDATE ON user_api_configs
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            ''')

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Personal Data Center database tables initialized")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)

    # ==================== API 配置操作 ====================

    def get_api_config(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的 API 配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                'SELECT * FROM user_api_configs WHERE user_id = %s',
                (user_id,)
            )

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Error getting API config: {e}")
            return None

    def save_api_config(
        self,
        user_id: str,
        api_provider: str,
        api_key: Optional[str],
        api_base_url: Optional[str] = None,
        model_name: str = 'anthropic/claude-3.5-sonnet',
        use_system_config: bool = False,
        system_url_idx: Optional[int] = None
    ) -> bool:
        """保存用户的 API 配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 使用 UPSERT (INSERT ... ON CONFLICT)
            cursor.execute('''
                INSERT INTO user_api_configs
                (user_id, api_provider, api_key, api_base_url, model_name, use_system_config, system_url_idx)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    api_provider = EXCLUDED.api_provider,
                    api_key = EXCLUDED.api_key,
                    api_base_url = EXCLUDED.api_base_url,
                    model_name = EXCLUDED.model_name,
                    use_system_config = EXCLUDED.use_system_config,
                    system_url_idx = EXCLUDED.system_url_idx,
                    updated_at = CURRENT_TIMESTAMP
            ''', (user_id, api_provider, api_key, api_base_url, model_name, use_system_config, system_url_idx))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error saving API config: {e}")
            return False

    # ==================== 对话历史操作 ====================

    def save_chat_message(
        self,
        user_id: str,
        role: str,
        content: str,
        files: Optional[List[Dict]] = None
    ) -> bool:
        """保存单条对话消息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            files_json = json.dumps(files) if files else None

            cursor.execute('''
                INSERT INTO chat_history (user_id, role, content, files)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, role, content, files_json))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error saving chat message: {e}")
            return False

    def get_chat_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取用户的对话历史"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('''
                SELECT id, role, content, files, created_at
                FROM chat_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            ''', (user_id, limit))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            # 反转顺序，最早的消息在前
            messages = []
            for row in reversed(rows):
                msg = dict(row)
                # 解析 JSON 文件数据
                if msg.get('files'):
                    try:
                        msg['files'] = json.loads(msg['files']) if isinstance(msg['files'], str) else msg['files']
                    except:
                        msg['files'] = None
                messages.append(msg)

            return messages

        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []

    def clear_chat_history(self, user_id: str) -> bool:
        """清空用户的对话历史"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                'DELETE FROM chat_history WHERE user_id = %s',
                (user_id,)
            )

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error clearing chat history: {e}")
            return False

    # ==================== 🆕 学生档案文件操作 ====================

    def save_profile_file(
        self,
        user_id: str,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size: int,
        description: Optional[str] = None,
        category: str = 'other'
    ) -> Optional[int]:
        """保存档案文件信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO profile_files
                (user_id, file_name, file_path, file_type, file_size, description, category)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (user_id, file_name, file_path, file_type, file_size, description, category))

            file_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return file_id

        except Exception as e:
            logger.error(f"Error saving profile file: {e}")
            return None

    def get_profile_files(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有档案文件"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('''
                SELECT id, file_name, file_path, file_type, file_size,
                       description, category, created_at
                FROM profile_files
                WHERE user_id = %s
                ORDER BY created_at DESC
            ''', (user_id,))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting profile files: {e}")
            return []

    def delete_profile_file(self, user_id: str, file_id: int) -> bool:
        """删除档案文件"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 先获取文件路径用于删除物理文件
            cursor.execute(
                'SELECT file_path FROM profile_files WHERE id = %s AND user_id = %s',
                (file_id, user_id)
            )
            result = cursor.fetchone()

            if not result:
                cursor.close()
                conn.close()
                return False

            file_path = result[0]

            # 删除数据库记录
            cursor.execute(
                'DELETE FROM profile_files WHERE id = %s AND user_id = %s',
                (file_id, user_id)
            )

            conn.commit()
            cursor.close()
            conn.close()

            # 返回文件路径供调用者删除物理文件
            return file_path

        except Exception as e:
            logger.error(f"Error deleting profile file: {e}")
            return False

    def get_profile_file_by_id(self, user_id: str, file_id: int) -> Optional[Dict[str, Any]]:
        """获取单个档案文件信息"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('''
                SELECT id, file_name, file_path, file_type, file_size,
                       description, category, created_at
                FROM profile_files
                WHERE id = %s AND user_id = %s
            ''', (file_id, user_id))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            return dict(row) if row else None

        except Exception as e:
            logger.error(f"Error getting profile file: {e}")
            return None


# 创建全局实例
pdc_db = PersonalDataCenterDB()
