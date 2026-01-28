"""
统一认证服务模块 (Authorization Service)
负责处理飞书授权码 (PersonalBaseToken) 和 Base API 请求。
支持多用户模式，每个用户可以使用自己的授权码。
"""
import os
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# 飞书 Base API 域名 (国内版: https://base-api.feishu.cn, 国际版: https://base-api.larksuite.com)
BASE_API_DOMAIN = os.getenv("BASE_API_DOMAIN", "https://base-api.feishu.cn")

# 全局默认授权码（可选，主要用于后台管理功能）
PERSONAL_BASE_TOKEN = os.getenv("PERSONAL_BASE_TOKEN", "")

def get_base_authorization_header(base_token: Optional[str] = None) -> dict:
    """
    获取授权码请求头
    
    Args:
        base_token: 用户提供的授权码，如果不提供则使用全局默认值
    
    Returns:
        包含 Authorization 头的字典
    """
    token = base_token or PERSONAL_BASE_TOKEN
    if not token:
        logger.warning("No PersonalBaseToken provided and no default configured")
    return {"Authorization": f"Bearer {token}"}

def get_base_api_url(path: str) -> str:
    """获取完整的 Base API URL"""
    path = path.lstrip('/')
    return f"{BASE_API_DOMAIN.rstrip('/')}/{path}"
