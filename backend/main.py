import os
import time
import uuid
import logging
from typing import Optional

import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

APP_ID = os.getenv("APP_ID", "")
APP_SECRET = os.getenv("APP_SECRET", "")
PARENT_TYPE = os.getenv("PARENT_TYPE", "explorer")  # explorer | folder
PARENT_NODE = os.getenv("PARENT_NODE", "root")       # root or folder_token
BACKEND_BASE = os.getenv("BACKEND_BASE", "http://localhost:8000")

# API 文档配置
API_TITLE = "飞书签名插件 API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
## 飞书多维表格签名插件后端服务

提供用户签名上传、配额管理、表单分享等功能。

### 功能模块

* **签名上传** - 手写签名图片上传到飞书云空间
* **配额管理** - 用户使用次数和邀请码管理
* **表单分享** - 创建外部签名表单供匿名用户填写
* **OAuth 授权** - 飞书用户身份验证

### 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1100 | 配额不足 |
| 1300 | 表单不存在 |
| 1500 | 飞书API错误 |
"""

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "签名", "description": "签名上传相关接口"},
        {"name": "配额", "description": "配额查询和管理"},
        {"name": "表单", "description": "外部表单创建和提交"},
        {"name": "系统", "description": "健康检查等系统接口"},
    ]
)

# 导入自定义异常处理器
try:
    from errors import AppException, app_exception_handler, generic_exception_handler
    app.add_exception_handler(AppException, app_exception_handler)
    logger.info("Custom exception handlers registered")
except ImportError as e:
    logger.warning(f"Custom exception handlers not available: {e}")

# 导入并注册配额路由
from quota_router import router as quota_router
app.include_router(quota_router)
logger.info("Quota router registered successfully")

# 导入并注册表单路由
from form_router import router as form_router
app.include_router(form_router)
logger.info("Form router registered successfully")

# 导入并注册管理后台路由
from admin_router import router as admin_router
app.include_router(admin_router)
logger.info("Admin router registered successfully")

# 支付功能说明：已迁移到飞书官方付费能力
# 旧的第三方支付路由(payment_router.py)已废弃删除
# 现在使用飞书多维表格插件的官方付费功能，无需后端支付API
logger.info("Payment router registered successfully")

# 导入数据库初始化函数
from database import init_db

@app.on_event("startup")
async def startup_event():
    """应用启动时自动初始化数据库表"""
    try:
        init_db()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        # 不抛出异常，允许应用继续启动（表可能已存在）


# CORS 配置
# 生产环境应设置 CORS_ORIGINS 环境变量，如 "https://example.com,https://app.example.com"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
cors_origins = CORS_ORIGINS.split(",") if CORS_ORIGINS != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# 导入数据库模块（用于配额检查）
try:
    from database import get_db
    import quota_service
    DB_AVAILABLE = True
    logger.info("Database module loaded successfully")
except ImportError as e:
    DB_AVAILABLE = False
    logger.warning(f"Database module not available: {e}, using fallback mode")


# 导入统一认证服务
try:
    import auth_service
    logger.info("Auth service module loaded")
except ImportError as e:
    logger.error(f"Auth service module failed to load: {e}")

# user oauth tokens (已移除 OAuth，仅作兼容留空)
USER_TOKENS = {}


# ===== Upload signature =====

# ===== Upload signature =====

@app.post("/api/sign/upload", tags=["签名"], summary="上传签名文件")
async def upload_signature(
    file: UploadFile = File(..., description="签名图片文件"),
    open_id: str = Form(..., description="用户 open_id"),
    tenant_key: str = Form(..., description="租户 key"),
    file_name: str = Form("signature.png", description="文件名"),
    folder_token: Optional[str] = Form(None, description="目标文件夹 token"),
    has_quota: int = Form(0, description="飞书官方付费权益 (1=有权益, 0=无)"),
):
    """
    上传签名文件到飞书云空间（使用授权码模式）。
    
    - **身份识别**: 使用前端获取的 open_id
    - **鉴权模式**: 使用 PersonalBaseToken (授权码)
    - **付费权益**: 如果 has_quota=1，跳过本地配额扣减
    """
    # Debug logging
    logger.info(f"Upload request (BaseToken mode): open_id={open_id}, folder_token={folder_token}, file_name={file_name}, has_quota={has_quota}")
    
    # 1) 配额检查
    consume_quota_after = False
    if has_quota == 1:
        logger.info(f"Feishu official quota valid for {open_id}, skipping local quota check")
        consume_quota_after = False
    elif DB_AVAILABLE:
        from user_db_manager import ensure_user_database, get_user_session
        user_key = f"{open_id}::{tenant_key}"
        ensure_user_database(user_key)
        user_db = get_user_session(user_key)
        try:
            chk = quota_service.check_can_sign(user_db, db, open_id, tenant_key)
            if not chk["can_sign"]:
                raise HTTPException(status_code=402, detail="NO_QUOTA")
            consume_quota_after = chk.get("consume_quota", True)
        finally:
            user_db.close()
    else:
        logger.warning("Database not available, skipping quota check")
        consume_quota_after = False

    # 2) 保存本地存档
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="EMPTY_FILE")
    try:
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        base, ext = os.path.splitext(file_name)
        safe_ext = ext if ext else '.png'
        ts = int(time.time() * 1000)
        local_name = f"{base}_{ts}{safe_ext}"
        local_path = os.path.join(uploads_dir, local_name)
        with open(local_path, 'wb') as f_out:
            f_out.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"save local failed: {e}")

    # 3) 构建上传请求
    headers = auth_service.get_base_authorization_header()
    parent_type = "explorer"
    parent_node = ""

    if folder_token:
        parent_type = "folder"
        parent_node = folder_token
        logger.info(f"Using provided folder_token: {folder_token}")
    else:
        # 使用个人空间根目录 (授权码模式下 drive 接口支持上传到素材)
        logger.info("Using personal space root directory")
        parent_type = "explorer"
        parent_node = ""

    # 使用授权码专用的域名
    url_upload = auth_service.get_base_api_url("/open-apis/drive/v1/files/upload_all")
    
    file_size = len(content)
    form_data = {
        "file_name": file_name,
        "parent_type": parent_type,
        "size": str(file_size),
    }
    
    if parent_node and parent_node != "root":
        form_data["parent_node"] = parent_node

    files = {"file": (file_name, content, file.content_type or "image/png")}
    
    logger.info(f"Uploading to Feishu Base API: url={url_upload}")
    
    try:
        r = requests.post(
            url_upload,
            data=form_data,
            files=files,
            headers=headers,
            timeout=30
        )
        logger.info(f"Feishu response: status={r.status_code}")
    except Exception as e:
        logger.error(f"Upload request exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"upload request failed: {str(e)}")

    # 4) 解析响应
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"upload_all failed: status={r.status_code}")
    
    try:
        data = r.json()
    except:
        raise HTTPException(status_code=500, detail="upload_all response is not valid JSON")

    if data.get("code") != 0:
        raise HTTPException(status_code=500, detail=f"upload_all failed: {data}")

    d = data.get("data") or {}
    file_token = d.get("file_token") or d.get("token")
    if not file_token:
        raise HTTPException(status_code=500, detail="no file_token in response")

    # 5) 消耗配额
    if consume_quota_after and DB_AVAILABLE:
        from user_db_manager import ensure_user_database, get_user_session
        user_key = f"{open_id}::{tenant_key}"
        ensure_user_database(user_key)
        user_db = get_user_session(user_key)
        try:
            quota_service.consume_quota(user_db, db, open_id, tenant_key, file_token, file_name)
        finally:
            user_db.close()

    return {"file_token": file_token, "local_path": local_path}



# Health check

# Health check
@app.get("/healthz", tags=["系统"], summary="健康检查")
def healthz():
    """服务健康检查端点，用于监控和负载均衡。"""
    return {"ok": True}


# ===== 启动入口 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
