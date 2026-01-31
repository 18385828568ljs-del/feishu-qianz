"""
认证依赖注入模块
提供统一的用户认证依赖函数
"""
from typing import Optional
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from auth_jwt import decode_token

bearer_scheme = HTTPBearer()


def get_current_user_info(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> dict:
    """
    获取当前用户信息的依赖函数
    
    从 JWT Token 中提取用户信息，并返回完整的用户数据
    
    Returns:
        dict: {
            'user_id': int,
            'open_id': str,
            'tenant_key': str
        }
    """
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="NOT_AUTHENTICATED")
    
    try:
        payload = decode_token(creds.credentials)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"INVALID_TOKEN: {str(e)}")
    
    # 从 JWT payload 中提取信息
    user_id = payload.get("user_id")
    open_id = payload.get("open_id")
    tenant_key = payload.get("tenant_key")
    
    if not user_id or not open_id or not tenant_key:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN_PAYLOAD")
    
    return {
        'user_id': user_id,
        'open_id': open_id,
        'tenant_key': tenant_key
    }


def get_optional_user_info(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """
    可选的用户信息获取（不强制要求 Token）
    
    用于某些公开接口，如果有 Token 则验证，没有则返回 None
    
    Returns:
        Optional[dict]: 用户信息或 None
    """
    if not authorization or not authorization.startswith('Bearer '):
        return None
    
    try:
        token = authorization.replace('Bearer ', '')
        payload = decode_token(token)
        
        user_id = payload.get("user_id")
        open_id = payload.get("open_id")
        tenant_key = payload.get("tenant_key")
        
        if not user_id or not open_id or not tenant_key:
            return None
        
        return {
            'user_id': user_id,
            'open_id': open_id,
            'tenant_key': tenant_key
        }
    except Exception:
        return None
