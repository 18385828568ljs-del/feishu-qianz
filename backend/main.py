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
        {"name": "授权", "description": "OAuth 用户授权"},
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
        
        # 执行数据库迁移（添加 record_index 字段）
        try:
            from migrations.add_record_index import migrate
            migrate()
        except ImportError:
            # 如果迁移脚本不存在，跳过（不影响启动）
            pass
        except Exception as e:
            logger.warning(f"Database migration warning: {e}")
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

# user oauth tokens (使用 MySQL/Redis 存储，支持多实例部署)
# 优先级：Redis（如果配置） -> MySQL -> 内存存储
try:
    from session_store import USER_TOKENS
    logger.info("Session storage module loaded")
except ImportError:
    USER_TOKENS = {}
    logger.warning("session_store not available, using in-memory storage")


def get_tenant_access_token() -> str:
    if not APP_ID or not APP_SECRET:
        raise HTTPException(status_code=500, detail="APP_ID/APP_SECRET not configured")
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    data = resp.json()
    if data.get("code") != 0:
        raise HTTPException(status_code=500, detail=f"get tenant_access_token failed: {data}")
    return data["tenant_access_token"]


def _parse_json_response(r: requests.Response):
    """Parse Feishu response, handling potential XSSI prefix."""
    try:
        return r.json()
    except Exception:
        text = r.text if hasattr(r, 'text') else ''
        if text.startswith(")]}\'"):
            try:
                cleaned = text.split('\n', 1)[-1] if '\n' in text else text[4:]
                import json as _json
                return _json.loads(cleaned)
            except Exception:
                pass
        ctype = r.headers.get('content-type') if hasattr(r, 'headers') else None
        raise HTTPException(status_code=500, detail=f"non-json response: status={r.status_code}, content_type={ctype}, body={text[:500]}")


def get_user_root_folder_token(access_token: str) -> Optional[str]:
    """Try to get user's root folder token. Return None when fails (will fallback)."""
    url = "https://open.feishu.cn/open-apis/drive/v1/files/root_folder/meta"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        logger.info(f"Calling Feishu root_folder/meta API...")
        r = requests.get(url, headers=headers, timeout=10)
        logger.info(f"root_folder/meta response: status={r.status_code}")
        
        # 先检查状态码，404 或其他错误状态码直接返回 None，不尝试解析 JSON
        if r.status_code != 200:
            logger.warning(f"root_folder/meta returned status={r.status_code}, will use fallback (explorer without parent_node)")
            return None
        
        # 只有 200 状态码才尝试解析 JSON
        try:
            data = r.json()
        except Exception as json_err:
            logger.warning(f"root_folder/meta response is not valid JSON: {json_err}, will use fallback")
            return None
        
        if data.get("code") != 0:
            logger.warning(f"root_folder/meta returned code={data.get('code')}, msg={data.get('msg')}, will use fallback")
            return None
        
        d = data.get("data", {})
        # Some tenants return token under data.token, others under data.file.token
        token = d.get("token") or (d.get("file") or {}).get("token")
        if token:
            logger.info(f"Successfully got root folder token: {token[:20]}...")
        return token
    except Exception as ex:
        # Network error or other exceptions, fallback
        logger.warning(f"root_folder/meta exception: {str(ex)}, will use fallback")
        return None


# ===== OAuth for user_access_token (for personal/shared folders) =====
# 根据飞书官方文档：https://open.feishu.cn/document/ukTMukTMukTM/ukzN4UjL5EDO14SOkTNx

def get_redirect_uri(request: Request) -> str:
    """
    根据请求动态构建 redirect_uri。
    本地开发时使用实际请求的 host 和 port，生产环境使用 BACKEND_BASE。
    """
    request_host = request.url.hostname
    request_port = request.url.port
    request_scheme = request.url.scheme
    
    # 判断是否为本地开发环境
    is_local = request_host in ["localhost", "127.0.0.1"] or (
        request_port and request_port in [8000, 3000, 5000, 8080]
    )
    
    if is_local:
        # 本地开发：使用实际请求的 host 和 port
        if request_port:
            return f"{request_scheme}://{request_host}:{request_port}/auth/callback"
        else:
            return f"{request_scheme}://{request_host}/auth/callback"
    else:
        # 生产环境：使用 BACKEND_BASE 环境变量
        return f"{BACKEND_BASE}/auth/callback"

@app.get("/auth/start", tags=["授权"], summary="启动 OAuth 授权")
def auth_start(request: Request):
    """
    启动飞书 OAuth 授权流程。
    
    根据飞书官方文档，使用 authen/v1/index 接口启动授权。
    返回飞书授权页面 URL，前端需要跳转到该 URL 进行用户授权。
    
    参考文档：https://open.feishu.cn/document/ukTMukTMukTM/ukzN4UjL5EDO14SOkTNx
    """
    if not APP_ID or not APP_SECRET:
        logger.error("❌ APP_ID or APP_SECRET not configured")
        return JSONResponse({"error": "APP_ID or APP_SECRET not configured"}, status_code=500)
    
    state = str(uuid.uuid4())
    
    # 根据请求动态构建 redirect_uri（本地开发时自动检测，生产环境使用 BACKEND_BASE）
    redirect_uri = get_redirect_uri(request)
    
    # 根据飞书官方文档，需要请求云盘和多维表格相关权限
    # scope 参数用于指定需要申请的权限范围
    # drive:drive 表示云盘权限
    # bitable:app 表示多维表格应用权限（读写）
    # 参考：https://open.feishu.cn/document/ukTMukTMukTM/uYjL14iN2EjL2YTN
    url = (
        "https://open.feishu.cn/open-apis/authen/v1/index"
        f"?app_id={APP_ID}&redirect_uri={requests.utils.quote(redirect_uri)}&state={state}"
        # 添加权限范围：云盘权限 + 多维表格权限
        "&scope=drive:drive bitable:app"
    )
    logger.info(f"Auth start: redirect_uri={redirect_uri}")
    return JSONResponse({"auth_url": url, "state": state, "redirect_uri": redirect_uri})


@app.get("/auth/callback", tags=["授权"], summary="OAuth 回调")
def auth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, error_description: Optional[str] = None):
    """
    OAuth 授权回调端点，由飞书自动跳转。
    
    根据飞书官方文档，飞书会在用户授权后重定向到此端点，并携带 code 参数。
    后端使用 code 交换 access_token。
    
    参考文档：https://open.feishu.cn/document/ukTMukTMukTM/ukzN4UjL5EDO14SOkTNx
    
    重要：此端点必须在飞书开放平台后台的「安全设置」->「重定向URL」中配置。
    redirect_uri 必须与代码中的 BACKEND_BASE + /auth/callback 完全一致。
    """
    # 检查是否有错误参数（飞书在授权失败时会返回 error 参数）
    if error:
        error_msg = f"飞书返回错误: {error}"
        if error_description:
            error_msg += f" - {error_description}"
        logger.error(f"Auth callback error: {error}, description: {error_description}")
        expected_redirect_uri = get_redirect_uri(request)
        actual_backend_base = request.url.scheme + "://" + request.url.hostname + (f":{request.url.port}" if request.url.port else "")
        return JSONResponse({
            "error": "authorization_failed",
            "feishu_error": error,
            "feishu_error_description": error_description,
            "message": error_msg,
            "expected_redirect_uri": expected_redirect_uri,
            "help_url": f"{actual_backend_base}/auth/diagnose"
        }, status_code=400)
    
    if not code:
        logger.error(f"Auth callback: Missing code parameter")
        expected_redirect_uri = get_redirect_uri(request)
        actual_backend_base = request.url.scheme + "://" + request.url.hostname + (f":{request.url.port}" if request.url.port else "")
        return JSONResponse({
            "error": "missing code",
            "message": "授权失败：未收到授权码",
            "expected_redirect_uri": expected_redirect_uri,
            "help_url": f"{actual_backend_base}/auth/diagnose"
        }, status_code=400)
    
    # 根据飞书官方文档，使用 authorization_code 交换 access_token
    # 参考：https://open.feishu.cn/document/ukTMukTMukTM/ukzN4UjL5EDO14SOkTNx
    token_url = "https://open.feishu.cn/open-apis/authen/v1/access_token"
    resp = requests.post(token_url, json={
        "grant_type": "authorization_code",
        "code": code,
        "app_id": APP_ID,
        "app_secret": APP_SECRET,
    }, timeout=15)
    try:
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to parse token response: {e}")
        return JSONResponse({"error": "invalid token response"}, status_code=500)

    if data.get("code") != 0:
        error_msg = data.get("msg", "unknown error")
        logger.error(f"Token exchange failed: code={data.get('code')}, msg={error_msg}")
        return JSONResponse({
            "error": "token exchange failed", 
            "feishu_code": data.get("code"),
            "feishu_msg": error_msg
        }, status_code=500)

    d = data.get("data", {})
    access_token = d.get("access_token")
    refresh_token = d.get("refresh_token")
    expires_in = d.get("expires_in", 7200)
    user_info = d.get("user_info") or {}

    if not access_token:
        return JSONResponse({"error": "no access_token in response", "resp": data}, status_code=500)

    # store by generated session id
    session_id = str(uuid.uuid4())
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": int(time.time()) + int(expires_in),
        "user": user_info,
    }
    
    try:
        USER_TOKENS[session_id] = token_data
        logger.info(f"Auth callback success: session_id={session_id}, user={user_info.get('name', 'unknown')}")
    except Exception as e:
        logger.error(f"Auth callback: Failed to store session: {e}", exc_info=True)
    # show a very small page to close window
    html = f"""
    <html><head><meta charset="UTF-8"></head><body>
    <script>
      console.log('Auth callback page loaded, session_id: {session_id}');
      try {{
        if (window.opener) {{
          console.log('Sending postMessage to opener...');
          window.opener.postMessage({{"type":"feishu-auth-done","session_id":"{session_id}"}}, "*");
          console.log('postMessage sent successfully');
        }} else {{
          console.warn('window.opener is null, cannot send message');
        }}
      }} catch (e) {{
        console.error('Error sending postMessage:', e);
      }}
      document.write('<p style="padding:20px;font-family:Arial;">授权成功，可以关闭此窗口。</p><p style="padding:0 20px;font-size:12px;color:#666;">SessionID: {session_id}</p>');
      // 3秒后自动关闭窗口
      setTimeout(function(){{ window.close(); }}, 3000);
    </script>
    </body></html>
    """
    return HTMLResponse(html)


@app.get("/auth/diagnose", tags=["授权"], summary="诊断授权配置")
def auth_diagnose(request: Request):
    """
    诊断端点，检查授权配置是否正确。
    帮助排查回调未到达的问题。
    """
    # 根据请求动态构建 redirect_uri
    redirect_uri = get_redirect_uri(request)
    
    # 判断是否为本地开发环境
    request_host = request.url.hostname
    request_port = request.url.port
    request_scheme = request.url.scheme
    is_local = request_host in ["localhost", "127.0.0.1"] or (
        request_port and request_port in [8000, 3000, 5000, 8080]
    )
    
    # 检查配置
    is_localhost = is_local or (BACKEND_BASE and ("localhost" in BACKEND_BASE.lower() or "127.0.0.1" in BACKEND_BASE))
    
    # 计算实际使用的后端地址（用于显示）
    if is_local:
        actual_backend_base = f"{request_scheme}://{request_host}" + (f":{request_port}" if request_port else "")
    else:
        actual_backend_base = BACKEND_BASE
    
    checks = {
        "backend_base": {
            "value": actual_backend_base,
            "status": "ok",  # 本地测试时也是正常状态
            "message": f"实际使用的后端地址: {actual_backend_base}" + ("（本地开发模式，自动检测）" if is_local else f"（生产环境，来自 BACKEND_BASE={BACKEND_BASE}）")
        },
        "app_id": {
            "value": APP_ID if APP_ID else "未配置",
            "status": "ok" if APP_ID else "error",
            "message": "APP_ID 已配置" if APP_ID else "APP_ID 未配置"
        },
        "app_secret": {
            "value": "已配置" if APP_SECRET else "未配置",
            "status": "ok" if APP_SECRET else "error",
            "message": "APP_SECRET 已配置" if APP_SECRET else "APP_SECRET 未配置"
        },
        "redirect_uri": {
            "value": redirect_uri,
            "status": "ok",
            "message": "当前使用的回调地址"
        }
    }
    
    # 生成检查清单（根据飞书官方文档）
    checklist = [
        "✅ 检查飞书开放平台后台配置（参考：https://open.feishu.cn/document/ukTMukTMukTM/ukzN4UjL5EDO14SOkTNx）：",
        f"   1. 登录 https://open.feishu.cn/app",
        f"   2. 进入你的应用（APP_ID: {APP_ID}）",
        f"   3. 找到「安全设置」->「重定向URL」",
        f"   4. 确保添加了以下地址（必须完全一致，包括协议、域名、路径）：",
        f"      {redirect_uri}",
        "",
        "⚠️  根据飞书官方文档，常见问题：",
        "   - redirect_uri 必须与飞书后台配置的完全一致（包括协议 http/https、端口号）",
        "   - 本地测试时，redirect_uri 必须包含端口号（如 http://localhost:8000/auth/callback）",
        "   - 确保飞书后台的 redirect_uri 列表包含上述地址",
        "   - 修改 redirect_uri 后，需要重新发布应用版本才能生效",
        "",
        "🔍 测试步骤：",
        f"   1. 访问 {actual_backend_base}/auth/start 获取授权URL",
        "   2. 在浏览器中打开授权URL并完成授权",
        "   3. 检查后端日志确认授权成功",
        "",
        "📚 飞书官方文档：",
        "   - OAuth 授权流程：https://open.feishu.cn/document/ukTMukTMukTM/ukzN4UjL5EDO14SOkTNx",
        "   - 权限说明：https://open.feishu.cn/document/ukTMukTMukTM/uYjL14iN2EjL2YTN",
    ]
    
    return JSONResponse({
        "status": "diagnostic",
        "checks": checks,
        "checklist": checklist,
        "current_request": {
            "url": str(request.url),
            "host": request.headers.get("host", "unknown"),
            "scheme": request.url.scheme
        },
        "timestamp": time.time()
    })


from fastapi.responses import HTMLResponse

@app.get("/auth/status", tags=["授权"], summary="查询授权状态")
def auth_status(session_id: Optional[str] = None):
    """查询用户授权状态，检查 session 是否有效。"""
    if not session_id:
        return {"authorized": False}
    
    try:
        stored_data = USER_TOKENS.get(session_id)
        if stored_data:
            return {
                "authorized": True,
                "expires_at": stored_data.get("expires_at"),
                "user": stored_data.get("user"),
            }
        
        # 尝试从 session_store 直接查询
        try:
            from session_store import get_session
            direct_data = get_session(session_id)
            if direct_data:
                return {
                    "authorized": True,
                    "expires_at": direct_data.get("expires_at"),
                    "user": direct_data.get("user"),
                }
        except Exception:
            pass
        
        return {"authorized": False}
    except Exception as e:
        logger.error(f"Auth status error: {e}", exc_info=True)
        return {"authorized": False}


# ===== Drive helper endpoints for frontend compatibility =====

@app.get("/api/drive/get_root_folder_meta")
@app.get("/api/drive/root_folder/meta")
def api_drive_root_meta(session_id: Optional[str] = None):
    """Return a parent_type/parent_node pair for user's root folder.
    This is provided for clients that want to obtain a valid parent for upload.
    """
    if not session_id or session_id not in USER_TOKENS:
        return {"ok": False, "error": "USER_NOT_AUTHORIZED"}
    access_token = USER_TOKENS[session_id]["access_token"]
    try:
        token = get_user_root_folder_token(access_token)
        if token:
            return {"ok": True, "parent_type": "folder", "parent_node": token}
        # Fallback works on some tenants - explorer/root is valid for user_access_token
        return {"ok": True, "parent_type": "explorer", "parent_node": "root"}
    except Exception as e:
        # If getting root folder token fails, still return fallback
        return {"ok": True, "parent_type": "explorer", "parent_node": "root", "warning": f"root_folder/meta failed, using fallback: {str(e)}"}


@app.get("/api/drive/folder/meta")
def drive_folder_meta(folder_token: str, use_user_token: int = 0, session_id: Optional[str] = None):
    """Debug helper: fetch folder meta using tenant or user token to verify accessibility."""
    headers = {}
    if use_user_token:
        if not session_id or session_id not in USER_TOKENS:
            raise HTTPException(status_code=401, detail="USER_NOT_AUTHORIZED")
        headers["Authorization"] = f"Bearer {USER_TOKENS[session_id]['access_token']}"
    else:
        headers["Authorization"] = f"Bearer {get_tenant_access_token()}"
    url = f"https://open.feishu.cn/open-apis/drive/v1/files/{folder_token}/meta"
    r = requests.get(url, headers=headers, timeout=15)
    data = None
    try:
        data = _parse_json_response(r)
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=f"meta non-json: status={r.status_code}, body={getattr(r,'text','')[:200]}")
    return data

# ===== Upload signature =====

@app.post("/api/sign/upload", tags=["签名"], summary="上传签名文件")
async def upload_signature(
    file: UploadFile = File(..., description="签名图片文件"),
    open_id: str = Form("anon", description="用户 open_id"),
    tenant_key: str = Form("anon", description="租户 key"),
    file_name: str = Form("signature.png", description="文件名"),
    use_user_token: int = Form(0, description="是否使用用户 token (1=是, 0=否)"),
    folder_token: Optional[str] = Form(None, description="目标文件夹 token"),
    session_id: Optional[str] = Form(None, description="用户会话 ID"),
    has_quota: int = Form(0, description="飞书官方付费权益 (1=有权益, 0=无)"),
):
    """
    上传签名文件到飞书云空间。
    
    - **用户模式**: 使用 use_user_token=1 和有效的 session_id
    - **应用模式**: 使用 use_user_token=0 和 folder_token
    - **付费权益**: 如果 has_quota=1（飞书官方付费用户），跳过本地配额扣减
    
    返回文件 token 和本地存储路径。
    """
    # Debug logging
    logger.info(f"Upload request: use_user_token={use_user_token}, session_id={session_id}, folder_token={folder_token}, file_name={file_name}, has_quota={has_quota}")
    
    # 1) 配额检查（使用数据库服务）
    # 如果飞书官方付费权益有效 (has_quota=1)，直接允许且不扣本地配额
    consume_quota_after = False
    if has_quota == 1:
        logger.info(f"Feishu official quota valid for {open_id}, skipping local quota check")
        consume_quota_after = False
    elif DB_AVAILABLE:
        db = next(get_db())
        try:
            chk = quota_service.check_can_sign(db, open_id, tenant_key)
            if not chk["can_sign"]:
                raise HTTPException(status_code=402, detail="NO_QUOTA")
            consume_quota_after = chk.get("consume_quota", True)
        finally:
            db.close()
    else:
        # 如果数据库不可用，默认允许（用于开发测试）
        logger.warning("Database not available, skipping quota check")
        consume_quota_after = False

    # 2) Read content ONCE and save to local archive first (even if remote upload fails)
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

    # 3) Choose token & parent
    headers = {}
    parent_type = PARENT_TYPE
    parent_node = PARENT_NODE

    root_token_used = None

    if use_user_token:
        if not session_id or session_id not in USER_TOKENS:
            raise HTTPException(status_code=401, detail=f"USER_NOT_AUTHORIZED: session_id={session_id}, available_sessions={list(USER_TOKENS.keys())[:3]}")
        access_token = USER_TOKENS[session_id]["access_token"]
        headers["Authorization"] = f"Bearer {access_token}"
        logger.info(f"Using user token, session_id={session_id}")
        # Prefer explicit folder_token if provided; otherwise try to use the real root folder token.
        if folder_token:
            parent_type = "folder"
            parent_node = folder_token
            logger.info(f"Using provided folder_token: {folder_token}")
        else:
            # 直接使用 fallback，不尝试获取根目录 token（因为该接口在某些租户不可用）
            # 根据飞书官方文档，个人空间根目录使用 explorer，parent_node 留空
            logger.info("Using personal space root directory (explorer without parent_node)")
            parent_type = "explorer"
            parent_node = None  # 个人空间根目录时，parent_node 应该留空，不传 "root"
    else:
        # app-level upload to enterprise (tenant) space requires a concrete folder token
        token = get_tenant_access_token()
        headers["Authorization"] = f"Bearer {token}"
        if folder_token:
            parent_type = "folder"
            parent_node = folder_token
        elif PARENT_TYPE == "folder" and PARENT_NODE and PARENT_NODE != "root":
            # allow configuring a default enterprise folder via env
            parent_type = "folder"
            parent_node = PARENT_NODE
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "TENANT_UPLOAD_NEEDS_FOLDER_TOKEN: 使用企业(tenant)凭证上传时，需要指定目标文件夹的folder_token。"
                    "请在请求中传 folder_token，或将环境变量 PARENT_TYPE=folder 且 PARENT_NODE=<有效folder_token>。"
                    "若要上传到个人空间，请改用 use_user_token=1 并提供有效 session_id。"
                ),
            )

    # 4) Upload to Feishu for attachment display, reuse the same content
    # 重要：多维表格附件字段需要使用 files/upload_all 接口，而不是 medias/upload_all
    # medias/upload_all 返回的 token 只能用于即时消息等场景
    # 参考：https://open.feishu.cn/document/server-docs/docs/drive-v1/upload/upload_all
    url_upload = "https://open.feishu.cn/open-apis/drive/v1/files/upload_all"
    
    # files/upload_all 接口参数（form-data格式）：
    # - file_name: 文件名
    # - parent_type: 上传位置类型（explorer 表示个人云空间根目录）
    # - parent_node: 上传位置的标识符（个人云空间根目录可留空）
    # - size: 文件大小（字节）
    # - file: 实际的文件内容
    
    file_size = len(content)
    
    # 对于个人空间根目录，如果 parent_node 是 "root"，可以留空
    form_data = {
        "file_name": file_name,
        "parent_type": parent_type,
        "size": str(file_size),
    }
    
    # 根据飞书官方文档，只有当 parent_node 有值且不是 "root" 时才传递
    # 个人空间根目录时，parent_node 应该留空（不传这个参数）
    if parent_node and parent_node != "root" and parent_node.strip():
        form_data["parent_node"] = parent_node
        logger.info(f"Including parent_node in form_data: {parent_node}")
    else:
        logger.info("parent_node is empty or 'root', not including in form_data (using personal space root)")
    
    files = {"file": (file_name, content, file.content_type or "image/png")}
    
    logger.info(f"Uploading to Feishu (official API): url={url_upload}")
    logger.info(f"Form data: file_name={file_name}, parent_type={parent_type}, parent_node={parent_node or '(empty)'}, size={file_size}")
    
    try:
        # 使用 multipart/form-data 格式上传
        r = requests.post(
            url_upload,
            data=form_data,
            files=files,
            headers=headers,
            timeout=30
        )
        logger.info(f"Feishu response: status={r.status_code}, content-type={r.headers.get('content-type')}")
        logger.info(f"Feishu response text (first 500 chars): {r.text[:500]}")
    except Exception as e:
        logger.error(f"Upload request exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"upload request failed: {str(e)}")

    # Parse response - 先检查状态码
    if r.status_code != 200:
        response_text = r.text[:500] if hasattr(r, 'text') else 'N/A'
        logger.error(f"Feishu upload_all returned non-200 status: {r.status_code}, response: {response_text}")
        raise HTTPException(
            status_code=500,
            detail=f"upload_all failed: status={r.status_code}, response={response_text}"
        )
    
    # 只有 200 状态码才尝试解析 JSON
    try:
        data = r.json()
        logger.info(f"Feishu response parsed: {data}")
    except Exception as json_err:
        response_text = r.text[:500] if hasattr(r, 'text') else 'N/A'
        logger.error(f"Feishu response is not valid JSON: {json_err}, response: {response_text}")
        raise HTTPException(
            status_code=500,
            detail=f"upload_all response is not valid JSON: status={r.status_code}, error={str(json_err)}, response={response_text}"
        )

    if data.get("code") != 0:
        error_msg = data.get("msg", "unknown")
        error_code = data.get("code", "unknown")
        logger.error(f"Feishu API error: code={error_code}, msg={error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"upload_all failed: code={error_code}, msg={error_msg}, full_response={data}"
        )

    d = data.get("data") or {}
    file_token = d.get("file_token") or d.get("token")
    if not file_token:
        raise HTTPException(status_code=500, detail=f"upload_all succeeded but no file_token in response: {data}")

    # 5) 消耗配额（使用数据库服务）
    if consume_quota_after and DB_AVAILABLE:
        db = next(get_db())
        try:
            quota_service.consume_quota(db, open_id, tenant_key, file_token, file_name)
            logger.info(f"Quota consumed for {open_id}")
        except Exception as e:
            logger.warning(f"Failed to consume quota: {e}")
        finally:
            db.close()

    return {"file_token": file_token, "local_path": local_path, "parent_type": parent_type, "parent_node": parent_node}


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
