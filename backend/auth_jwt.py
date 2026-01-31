"""
JWT Token 认证模块
提供 JWT Token 的生成和验证功能
"""
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import HTTPException, status

load_dotenv()

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALG = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

# 尝试导入 PyJWT
try:
    import jwt
except ImportError:
    jwt = None


def _require_deps():
    """检查依赖是否已安装"""
    if jwt is None:
        raise RuntimeError("Missing dependency: PyJWT")


def create_access_token(user_id: int, open_id: str, tenant_key: str) -> str:
    """
    创建 JWT Token
    
    Args:
        user_id: 用户ID（app_user_identities表的主键）
        open_id: 飞书用户ID
        tenant_key: 租户Key
        
    Returns:
        JWT Token字符串
    """
    _require_deps()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),  # 标准JWT字段，存储主体标识
        "user_id": user_id,   # 用户ID
        "open_id": open_id,   # 飞书用户ID
        "tenant_key": tenant_key,  # 租户Key
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    """
    解码并验证 JWT Token
    
    Args:
        token: JWT Token字符串
        
    Returns:
        Token payload字典
        
    Raises:
        HTTPException: Token无效或过期
    """
    _require_deps()
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_TOKEN")
