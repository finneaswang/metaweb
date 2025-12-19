from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import uuid
from pathlib import Path
from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.metaweb.services.ai_service import chat_with_ai_assistant, test_api_key, list_models
from open_webui.metaweb.services.pdc_db_service import pdc_db

router = APIRouter()

# 文件上传目录
UPLOAD_DIR = Path("/home/linuxuser/openwebui-custom/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 档案文件上传目录
PROFILE_FILES_DIR = Path("/home/linuxuser/openwebui-custom/profile_files")
PROFILE_FILES_DIR.mkdir(parents=True, exist_ok=True)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    files: Optional[List[str]] = None
    chat_history: Optional[List[ChatMessage]] = None
    model_name: Optional[str] = None  # Selected model from frontend

class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None

class AIConfigForm(BaseModel):
    api_provider: str = 'openrouter'
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_name: str = 'anthropic/claude-3.5-sonnet'
    use_system_config: bool = False
    system_url_idx: Optional[int] = None

class ModelListForm(BaseModel):
    api_provider: str = 'openrouter'
    api_key: str
    api_base_url: Optional[str] = None


def _unwrap(value):
    return value.value if hasattr(value, "value") else value


@router.get("/system-connections")
async def get_system_connections(request: Request, user: UserModel = Depends(get_verified_user)):
    """返回系统（管理员）已配置的 OpenAI-compatible 连接列表（不包含 key）"""
    base_urls = list(_unwrap(request.app.state.config.OPENAI_API_BASE_URLS) or [])
    keys = list(_unwrap(request.app.state.config.OPENAI_API_KEYS) or [])
    configs = _unwrap(request.app.state.config.OPENAI_API_CONFIGS) or {}

    connections = []
    for idx, url in enumerate(base_urls):
        key = keys[idx] if idx < len(keys) else ""
        if not key:
            continue

        api_config = configs.get(str(idx), configs.get(url, {})) if isinstance(configs, dict) else {}
        if isinstance(api_config, dict) and api_config.get("enable", True) is False:
            continue

        label = None
        if isinstance(api_config, dict):
            label = api_config.get("prefix_id") or None

        safe_url = url.replace("https://", "").replace("http://", "")
        safe_url = safe_url.split("/")[0] if safe_url else f"connection-{idx}"

        connections.append(
            {
                "url_idx": idx,
                "label": label or safe_url,
            }
        )

    return {"connections": connections, "count": len(connections)}

class TestKeyResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None

@router.post("/upload-files")
async def upload_files(
    files: List[UploadFile] = File(...),
    user: UserModel = Depends(get_verified_user)
):
    """上传临时文件并返回URLs（用于对话）"""
    try:
        uploaded_urls = []

        for file in files:
            # 生成唯一文件名
            file_ext = Path(file.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = UPLOAD_DIR / unique_filename

            # 保存文件
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            # 返回文件路径
            uploaded_urls.append(str(file_path))

        return {"urls": uploaded_urls, "count": len(uploaded_urls)}

    except Exception as e:
        print(f"File Upload Error: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

# ==================== 🆕 档案文件管理 API ====================

@router.post("/profile-files/upload")
async def upload_profile_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    category: str = Form("other"),
    user: UserModel = Depends(get_verified_user)
):
    """上传学生档案文件（升学报告、测试成绩等）"""
    try:
        # 生成唯一文件名
        file_ext = Path(file.filename).suffix
        unique_filename = f"{user.id}_{uuid.uuid4()}{file_ext}"
        file_path = PROFILE_FILES_DIR / unique_filename

        # 保存文件
        contents = await file.read()
        file_size = len(contents)

        with open(file_path, "wb") as f:
            f.write(contents)

        # 保存到数据库
        file_id = pdc_db.save_profile_file(
            user_id=user.id,
            file_name=file.filename,
            file_path=str(file_path),
            file_type=file.content_type or 'application/octet-stream',
            file_size=file_size,
            description=description,
            category=category
        )

        if file_id:
            return {
                "success": True,
                "file_id": file_id,
                "file_name": file.filename,
                "message": "档案文件上传成功"
            }
        else:
            raise HTTPException(status_code=500, detail="文件保存失败")

    except Exception as e:
        print(f"Profile File Upload Error: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.get("/profile-files/list")
async def get_profile_files(user: UserModel = Depends(get_verified_user)):
    """获取用户的所有档案文件"""
    try:
        files = pdc_db.get_profile_files(user.id)
        return {
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        print(f"Get Profile Files Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/profile-files/{file_id}")
async def delete_profile_file(
    file_id: int,
    user: UserModel = Depends(get_verified_user)
):
    """删除档案文件"""
    try:
        file_path = pdc_db.delete_profile_file(user.id, file_id)

        if file_path:
            # 删除物理文件
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete physical file: {e}")

            return {
                "success": True,
                "message": "文件已删除"
            }
        else:
            raise HTTPException(status_code=404, detail="文件不存在")

    except Exception as e:
        print(f"Delete Profile File Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== API 配置 ====================

@router.get("/config")
async def get_ai_config(user: UserModel = Depends(get_verified_user)):
    """获取用户的 API 配置"""
    try:
        config = pdc_db.get_api_config(user.id)
        return config
    except Exception as e:
        print(f"Get AI Config Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/config")
async def save_ai_config(
    config_form: AIConfigForm,
    user: UserModel = Depends(get_verified_user)
):
    """保存用户的 API 配置"""
    try:
        if not config_form.use_system_config and not config_form.api_key:
            raise HTTPException(status_code=400, detail="API Key 不能为空")

        success = pdc_db.save_api_config(
            user_id=user.id,
            api_provider=config_form.api_provider,
            api_key=config_form.api_key,
            api_base_url=config_form.api_base_url,
            model_name=config_form.model_name,
            use_system_config=config_form.use_system_config,
            system_url_idx=config_form.system_url_idx
        )

        if success:
            return {"success": True, "message": "配置已保存"}
        else:
            raise HTTPException(status_code=500, detail="保存失败")

    except Exception as e:
        print(f"Save AI Config Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-key", response_model=TestKeyResponse)
async def test_api_key_endpoint(
    config_form: AIConfigForm,
    user: UserModel = Depends(get_verified_user)
):
    """测试 API Key 是否有效"""
    try:
        result = await test_api_key(
            api_provider=config_form.api_provider,
            api_key=config_form.api_key,
            api_base_url=config_form.api_base_url,
            model_name=config_form.model_name
        )

        if result["success"]:
            return TestKeyResponse(
                success=True,
                message="API Key 测试成功"
            )
        else:
            return TestKeyResponse(
                success=False,
                message="API Key 测试失败",
                error=result.get("error", "未知错误")
            )
    except Exception as e:
        return TestKeyResponse(
            success=False,
            message="测试过程出错",
            error=str(e)
        )

# ==================== 模型列表 ====================

@router.post("/models")
async def get_models_endpoint(
    form: ModelListForm,
    user: UserModel = Depends(get_verified_user)
):
    """获取模型列表（用户级别，不要求管理员权限）"""
    try:
        result = await list_models(
            api_provider=form.api_provider,
            api_key=form.api_key,
            api_base_url=form.api_base_url,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 对话历史 API ====================

@router.get("/history")
async def get_chat_history_endpoint(user: UserModel = Depends(get_verified_user)):
    """获取用户的对话历史"""
    try:
        messages = pdc_db.get_chat_history(user.id, limit=50)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        print(f"Get Chat History Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history")
async def clear_chat_history_endpoint(user: UserModel = Depends(get_verified_user)):
    """清空用户的对话历史"""
    try:
        success = pdc_db.clear_chat_history(user.id)
        if success:
            return {"success": True, "message": "对话历史已清空"}
        else:
            raise HTTPException(status_code=500, detail="清空失败")
    except Exception as e:
        print(f"Clear Chat History Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== AI 对话 API ====================

@router.post("/chat", response_model=ChatResponse)
async def ai_assistant_chat(
    http_request: Request,
    request: ChatRequest,
    user: UserModel = Depends(get_verified_user)
):
    """AI学习助手聊天接口 - 使用系统配置的AI连接"""
    try:
        # 转换chat_history为字典列表
        chat_history = None
        if request.chat_history:
            chat_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.chat_history
            ]

        # 始终使用系统配置的第一个可用连接
        base_urls = list(_unwrap(http_request.app.state.config.OPENAI_API_BASE_URLS) or [])
        keys = list(_unwrap(http_request.app.state.config.OPENAI_API_KEYS) or [])

        system_connection = None
        for idx, url in enumerate(base_urls):
            key = keys[idx] if idx < len(keys) else ""
            if key:  # 找到第一个有效的连接
                system_connection = {"api_base_url": url, "api_key": key}
                break

        if not system_connection:
            return ChatResponse(
                response="AI助手未配置。请联系管理员在后台配置AI连接。",
                success=False,
                error="No system connection available"
            )

        # 获取用户保存的模型偏好，或使用前端传来的模型
        model_name = request.model_name
        if not model_name:
            user_config = pdc_db.get_api_config(user.id) or {}
            model_name = user_config.get("model_name", "gpt-4o-mini")

        # 调用AI助手 (会自动读取档案文件和长期记忆)
        response = await chat_with_ai_assistant(
            user_id=user.id,
            user_message=request.message,
            file_paths=request.files,
            chat_history=chat_history,
            system_connection=system_connection,
            model_name=model_name
        )

        # 保存用户消息到数据库
        file_info = None
        if request.files:
            file_info = [{"url": url} for url in request.files]

        pdc_db.save_chat_message(
            user_id=user.id,
            role="user",
            content=request.message,
            files=file_info
        )

        # 保存AI回复到数据库
        pdc_db.save_chat_message(
            user_id=user.id,
            role="assistant",
            content=response,
            files=None
        )

        return ChatResponse(
            response=response,
            success=True
        )

    except Exception as e:
        print(f"AI Assistant Error: {e}")
        return ChatResponse(
            response="抱歉，AI助手遇到了问题，请稍后再试。",
            success=False,
            error=str(e)
        )

@router.get("/test")
async def test_ai_assistant(user: UserModel = Depends(get_verified_user)):
    """测试AI助手是否正常工作"""
    return {
        "status": "ok",
        "message": "AI Assistant is ready",
        "user_id": user.id
    }
