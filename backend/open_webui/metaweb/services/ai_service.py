import os
import json
import httpx
from typing import Optional, Dict, List, Any
from pathlib import Path
from open_webui.metaweb.services.pdc_db_service import pdc_db
from open_webui.metaweb.services.memory_service import memory_service
from open_webui.models.chats import Chats


async def get_student_learning_data(user_id: str) -> Dict[str, Any]:
    """
    获取学生的学习数据
    注意：这里从 OpenWebUI 的数据库读取（只读），不修改
    """
    chats_db = Chats()

    # 获取用户最近的聊天记录（最多10个）
    try:
        all_chats = chats_db.get_chats_by_user_id(user_id)

        # 提取聊天历史（最多10个最新的聊天）
        chat_history = []
        for chat in all_chats[:10]:
            if chat.chat and isinstance(chat.chat, dict):
                messages = chat.chat.get('messages', [])
                # 只保留最近5条消息的摘要
                recent_messages = messages[-5:] if len(messages) > 5 else messages

                chat_summary = {
                    'title': chat.title,
                    'created_at': chat.created_at,
                    'message_count': len(messages),
                    'recent_messages': [
                        {
                            'role': msg.get('role'),
                            'content': msg.get('content', '')[:200]  # 只保留前200字符
                        }
                        for msg in recent_messages
                    ]
                }
                chat_history.append(chat_summary)

        total_chats = len(all_chats)

    except Exception as e:
        print(f"Error reading chat history: {e}")
        chat_history = []
        total_chats = 0

    return {
        'user_id': user_id,
        'assignments': [],
        'chat_history': chat_history,
        'statistics': {
            'total_submissions': 0,
            'total_chats': total_chats,
            'average_score': 0
        }
    }


def read_file_content(file_path: str, max_length: int = 50000) -> str:
    """读取文件内容"""
    try:
        file_path_obj = Path(file_path)

        # 支持的文本文件格式
        text_extensions = ['.txt', '.md', '.py', '.js', '.json', '.csv', '.html', '.css']

        if file_path_obj.suffix.lower() in text_extensions:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 限制文件大小
                if len(content) > max_length:
                    return content[:max_length] + "\n\n[文件内容过长,已截断...]"
                return content
        elif file_path_obj.suffix.lower() == '.pdf':
            return "[PDF文件,暂不支持直接读取内容]"
        elif file_path_obj.suffix.lower() in ['.doc', '.docx']:
            return "[Word文档,暂不支持直接读取内容]"
        elif file_path_obj.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            return "[图片文件,暂不支持直接读取内容]"
        else:
            return f"[不支持的文件格式: {file_path_obj.suffix}]"
    except Exception as e:
        return f"[读取文件失败: {str(e)}]"


async def call_openrouter_api(
    messages: List[Dict[str, str]],
    api_key: str,
    api_base_url: str = 'https://openrouter.ai/api/v1',
    model: str = "anthropic/claude-3.5-sonnet",
    max_tokens: int = 2000
) -> Optional[str]:
    """调用 AI API"""
    if not api_key:
        return "API Key 未配置，请先在设置中配置 API Key"

    url = f"{api_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://metawebs.org",
        "X-Title": "MetaWeb AI Learning Assistant"
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

    except httpx.HTTPError as e:
        print(f"AI API Error: {e}")
        return f"API 调用失败: {str(e)}"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"未知错误: {str(e)}"


async def list_models(
    api_provider: str,
    api_key: str,
    api_base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """获取模型列表（用于前端下拉选择）"""
    if not api_key:
        return {"data": [], "error": "API Key 未配置"}

    if not api_base_url:
        if api_provider == 'openrouter':
            api_base_url = 'https://openrouter.ai/api/v1'
        elif api_provider == 'anthropic':
            api_base_url = 'https://api.anthropic.com/v1'
        elif api_provider == 'openai':
            api_base_url = 'https://api.openai.com/v1'
        else:
            api_base_url = 'https://openrouter.ai/api/v1'

    url = f"{api_base_url}/models"

    headers = {"Content-Type": "application/json"}

    if api_provider == 'anthropic':
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    # OpenRouter 建议加上来源信息，便于控制台统计
    if api_provider == 'openrouter':
        headers["HTTP-Referer"] = "https://metawebs.org"
        headers["X-Title"] = "MetaWeb"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return {
                    "data": [],
                    "error": f"获取模型列表失败: HTTP {response.status_code}",
                    "detail": response.text[:2000],
                }
            return response.json()
    except httpx.HTTPError as e:
        return {"data": [], "error": f"获取模型列表失败: {str(e)}"}
    except Exception as e:
        return {"data": [], "error": f"获取模型列表失败: {str(e)}"}


async def test_api_key(
    api_provider: str,
    api_key: str,
    api_base_url: Optional[str] = None,
    model_name: str = "anthropic/claude-3.5-sonnet"
) -> Dict[str, Any]:
    """测试 API Key 是否有效"""
    if not api_base_url:
        if api_provider == 'openrouter':
            api_base_url = 'https://openrouter.ai/api/v1'
        elif api_provider == 'anthropic':
            api_base_url = 'https://api.anthropic.com/v1'
        else:
            api_base_url = 'https://openrouter.ai/api/v1'

    test_messages = [
        {"role": "user", "content": "Say 'Hello!' in one word."}
    ]

    try:
        response = await call_openrouter_api(
            messages=test_messages,
            api_key=api_key,
            api_base_url=api_base_url,
            model=model_name,
            max_tokens=50
        )

        if response and not (
            response.startswith("API Key 未配置")
            or response.startswith("API 调用失败")
            or response.startswith("未知错误")
        ):
            return {"success": True, "message": "API Key 有效"}
        else:
            return {"success": False, "error": response}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def chat_with_ai_assistant(
    user_id: str,
    user_message: str,
    file_paths: Optional[List[str]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    system_connection: Optional[Dict[str, str]] = None,
    model_name: Optional[str] = None
) -> str:
    """AI学习助手主函数 - 使用系统配置的AI连接"""
    # 如果提供了系统连接，直接使用它
    if system_connection:
        user_config = {
            "api_provider": "system",
            "api_key": system_connection.get("api_key"),
            "api_base_url": system_connection.get("api_base_url"),
            "model_name": model_name or "gpt-4o-mini"
        }
    else:
        # 从独立数据库获取用户的 API 配置（兼容旧逻辑）
        user_config = pdc_db.get_api_config(user_id)
        if not user_config:
            return "AI助手未配置。请联系管理员配置AI连接。"

    # 使用传入的 model_name 覆盖配置中的模型
    if model_name:
        user_config["model_name"] = model_name

    # 获取学生学习数据
    student_data = await get_student_learning_data(user_id)

    # 🆕 获取学生档案文件
    profile_files = pdc_db.get_profile_files(user_id)

    # 构建档案文件上下文（读取文件内容）
    profile_context = ""
    if profile_files:
        profile_context = "\n\n学生档案背景资料:\n"
        for pf in profile_files:
            file_name = pf['file_name']
            file_path = pf['file_path']
            category = pf.get('category', 'other')
            description = pf.get('description', '')

            # 读取文件内容（限制每个文件5000字符）
            content = read_file_content(file_path, max_length=5000)

            profile_context += f"\n{file_name}"
            if description:
                profile_context += f" - {description}"
            profile_context += f" (类型: {category})\n"
            profile_context += f"```\n{content}\n```\n"

    # 🧠 检索相关的长期记忆
    retrieved_memories = memory_service.retrieve_memories(
        user_id=user_id,
        query=user_message,
        n_results=5
    )

    # 构建记忆部分的prompt
    memory_context = ""
    if retrieved_memories:
        memory_context = "\n\n相关记忆 (从之前的对话中记住的信息):\n"
        for i, mem in enumerate(retrieved_memories, 1):
            memory_context += f"{i}. {mem}\n"

    # 构建OpenWebUI聊天历史上下文
    chat_history_context = ""
    if student_data.get('chat_history'):
        chat_history_context = "\n\n**学生在OpenWebUI的历史对话记录:**\n"
        for i, chat in enumerate(student_data['chat_history'][:5], 1):  # 最多显示5个聊天
            chat_history_context += f"\n{i}. {chat.get('title', '未命名对话')} (共{chat.get('message_count', 0)}条消息)\n"
            if chat.get('recent_messages'):
                chat_history_context += "   最近对话片段:\n"
                for msg in chat['recent_messages'][-3:]:  # 每个聊天只显示最近3条
                    role_name = "学生" if msg['role'] == 'user' else "AI"
                    content = msg['content'][:150]  # 限制长度
                    chat_history_context += f"   - {role_name}: {content}...\n"

    # 构建System Prompt
    system_prompt = f"""你是MetaWeb AI学习助手，专门帮助学生分析学习情况并提供个性化建议。

**学生学习数据：**

- 统计信息：
- 总提交作业数：{student_data['statistics'].get('total_submissions', 0)}
- 平均分数：{student_data['statistics'].get('average_score', 0):.1f}
- OpenWebUI聊天记录数：{student_data['statistics'].get('total_chats', 0)}
{profile_context}{chat_history_context}{memory_context}
**你的角色：**
- 充分利用学生上传的档案资料（升学报告、测试成绩等）来了解学生背景
- **分析学生在OpenWebUI的历史对话，了解他们的学习兴趣、困难点和学习模式**
- 分析学生的学习数据，找出优势和薄弱点
- 提供具体、可操作的学习建议
- 预测学习趋势，帮助制定学习计划
- 如果学生上传了文件(作业、笔记等),请仔细分析文件内容并提供反馈
- 利用记忆功能，记住学生的偏好、学习进度和困难点
- 用友好、鼓励的语气交流
- 回答用中文

请基于以上数据回答学生的问题。"""

    # 构建消息列表
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # 添加历史对话 (最近6轮)
    if chat_history:
        messages.extend(chat_history[-6:])

    # 处理用户消息和临时上传的文件
    user_content = user_message

    # 如果有临时文件，读取文件内容并添加到消息中
    if file_paths and len(file_paths) > 0:
        file_contents = []
        for file_path in file_paths:
            file_name = Path(file_path).name
            content = read_file_content(file_path)
            file_contents.append(f"{file_name}:\n```\n{content}\n```")

        if file_contents:
            user_content = f"{user_message}\n\n**本次上传的文件：**\n\n" + "\n\n".join(file_contents)

    # 添加当前用户消息
    messages.append({"role": "user", "content": user_content})

    # 调用AI
    response = await call_openrouter_api(
        messages=messages,
        api_key=user_config['api_key'],
        api_base_url=user_config['api_base_url'] or 'https://openrouter.ai/api/v1',
        model=user_config['model_name']
    )

    # 🧠 对话后提取记忆并存储
    try:
        memories = await memory_service.extract_memories_from_conversation(
            user_message=user_message,
            ai_response=response,
            api_key=user_config['api_key'],
            api_base_url=user_config['api_base_url'] or 'https://openrouter.ai/api/v1',
            model=user_config['model_name']
        )

        # 存储提取的记忆
        for memory in memories:
            if memory and len(memory.strip()) > 5:  # 过滤太短的记忆
                memory_service.store_memory(
                    user_id=user_id,
                    memory_text=memory,
                    metadata={"source": "auto_extract"}
                )
    except Exception as e:
        print(f"Memory extraction failed: {e}")
        # 记忆提取失败不影响对话

    return response


# AI Service class for backward compatibility
class AIService:
    async def grade_submission(
        self,
        subject: str,
        grade_level: str,
        question_content: str,
        student_answer: str,
        total_points: int,
        grading_rubric: str = '',
        use_smart_model: bool = False
    ) -> Optional[Dict[str, Any]]:
        """评分提交的作业（向后兼容）"""
        return {
            'score': 0,
            'feedback': '评分功能暂未实现',
            'success': False
        }


# 创建单例实例供导入使用
ai_service = AIService()
