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

# 导入并注册用户初始化路由
from user_router import router as user_router
app.include_router(user_router)
logger.info("User router registered successfully")

# 导入并注册认证路由（旧版用户名密码，已隐藏文档）
# 注释掉：已改用 JWT 认证，不再需要旧的用户名密码认证
# from auth_router import router as auth_router
# app.include_router(auth_router)
# logger.info("Auth router registered successfully")

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
        # 初始化认证相关的表（已注释，使用JWT认证）
        # from auth_router import init_auth_tables
        # init_auth_tables()
        from user_router import init_user_tables
        init_user_tables()
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

# 导入认证依赖
try:
    from auth_dependencies import get_current_user_info
    logger.info("Auth dependencies loaded")
except ImportError as e:
    logger.error(f"Auth dependencies failed to load: {e}")

# user oauth tokens (已移除 OAuth，仅作兼容留空)
USER_TOKENS = {}


# ===== Upload signature =====

# ===== Upload signature =====

@app.post("/api/sign/upload", tags=["签名"], summary="上传签名文件")
async def upload_signature(
    request: Request,
    file: UploadFile = File(..., description="签名图片文件（必填）"),
    file_name: str = Form(..., min_length=1, description="文件名（必填）"),
    folder_token: str = Form(..., min_length=1, description="目标文件夹 token（必填）"),
    has_quota: int = Form(0, description="飞书官方付费权益 (1=有权益, 0=无)"),
    user_info: dict = Depends(get_current_user_info),
    db: Session = Depends(get_db),
):
    """
    上传签名文件到飞书云空间（使用授权码模式）。
    
    - **身份识别**: 从 JWT Token 中提取用户信息
    - **文件信息**: file_name 和 folder_token 必填
    - **鉴权模式**: 使用 PersonalBaseToken (授权码)
    - **付费权益**: 如果 has_quota=1，跳过本地配额扣减
    """
    # 从 JWT 中获取用户信息
    open_id = user_info['open_id']
    tenant_key = user_info['tenant_key']
    
    # 参数验证
    if not file_name:
        raise HTTPException(status_code=400, detail="file_name 为必填参数")
    
    if not folder_token:
        raise HTTPException(status_code=400, detail="folder_token 为必填参数")
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
            # 传入 shared_db (db)
            chk = quota_service.check_can_sign(user_db, db, open_id, tenant_key)
            if not chk["can_sign"]:
                raise HTTPException(status_code=402, detail="NO_QUOTA")
            consume_quota_after = chk.get("consume_quota", True)
        finally:
            user_db.close()
    else:
        logger.warning("Database not available, skipping quota check")
        consume_quota_after = False

    # 2) 读取文件内容 (不再保存本地存档)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="EMPTY_FILE")
    
    local_path = None  # 不再使用本地路径

    # 3) 构建上传请求
    # 从请求头获取用户的授权码
    user_base_token = request.headers.get('X-Base-Token', '')
    if not user_base_token:
        logger.error(f"No base token provided for user {open_id}")
        raise HTTPException(
            status_code=401, 
            detail="未提供授权码，请先在插件中配置您的飞书授权码"
        )
    
    logger.info(f"Using user-provided base token for {open_id}")
    
    try:
        headers = auth_service.get_base_authorization_header(user_base_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    # 使用指定的文件夹
    parent_type = "folder"
    parent_node = folder_token
    logger.info(f"Using folder_token: {folder_token}")

    # 使用 Open API 域名（Drive API 专用）
    url_upload = auth_service.get_open_api_url("/open-apis/drive/v1/files/upload_all")
    
    file_size = len(content)
    form_data = {
        "file_name": file_name,
        "parent_type": parent_type,
        "parent_node": parent_node,
        "size": str(file_size),
    }

    files = {"file": (file_name, content, file.content_type or "image/png")}
    
    logger.info(f"Uploading to Feishu Base API: url={url_upload}, folder={parent_node}")
    
    try:
        r = requests.post(
            url_upload,
            data=form_data,
            files=files,
            headers=headers,
            timeout=30
        )
        logger.info(f"Feishu response: status={r.status_code}")
        if r.status_code != 200:
            # 记录详细错误信息
            try:
                error_data = r.json()
                logger.error(f"Feishu API error details: {error_data}")
            except:
                logger.error(f"Feishu API error (non-JSON): {r.text[:500]}")
    except Exception as e:
        logger.error(f"Upload request exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"upload request failed: {str(e)}")

    # 4) 解析响应
    if r.status_code != 200:
        try:
            error_detail = r.json()
        except:
            error_detail = r.text[:200]
        raise HTTPException(status_code=500, detail=f"upload_all failed: status={r.status_code}, detail={error_detail}")
    
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
