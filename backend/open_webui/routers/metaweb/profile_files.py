"""
学生档案文件管理API
允许上传、查看、删除学生的背景资料文件（升学报告、测试成绩等）
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import uuid
from pathlib import Path
from open_webui.utils.auth import get_verified_user
from open_webui.models.users import UserModel
from open_webui.metaweb.services.pdc_db_service import pdc_db

router = APIRouter()

# 档案文件上传目录
PROFILE_FILES_DIR = Path("/home/linuxuser/openwebui-custom/profile_files")
PROFILE_FILES_DIR.mkdir(parents=True, exist_ok=True)

class ProfileFileInfo(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_size: int
    description: Optional[str]
    category: str
    created_at: str

@router.post("/upload")
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
                "message": "文件上传成功"
            }
        else:
            raise HTTPException(status_code=500, detail="文件保存失败")

    except Exception as e:
        print(f"Profile File Upload Error: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.get("/list")
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

@router.delete("/{file_id}")
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

@router.get("/test")
async def test_profile_files(user: UserModel = Depends(get_verified_user)):
    """测试档案文件API"""
    return {
        "status": "ok",
        "message": "Profile Files API is ready",
        "user_id": user.id
    }
