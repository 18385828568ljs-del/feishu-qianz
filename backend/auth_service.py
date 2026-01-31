"""
统一认证服务模块 (Authorization Service)
- 提供飞书 API 的 URL 构造
- 提供调用飞书 API 所需的认证头（使用服务端 tenant_access_token）
- 提供用户授权码模式的认证头（使用用户 PersonalBaseToken）
"""
import os
import logging
from typing import Dict

from dotenv import load_dotenv

from feishu_auth import feishu_auth

load_dotenv()
logger = logging.getLogger(__name__)

# 飞书 API 域名
# 多维表格 API 使用 base-api.feishu.cn
# 其他通用 API 使用 open.feishu.cn
BASE_API_DOMAIN = os.getenv("BASE_API_DOMAIN", "https://base-api.feishu.cn")
OPEN_API_DOMAIN = os.getenv("FEISHU_API_BASE", "https://open.feishu.cn")


def get_auth_header() -> Dict[str, str]:
    """
    获取调用飞书 API 所需的服务端认证头。
    内部使用 feishu_auth 服务自动管理 tenant_access_token。
    """
    return feishu_auth.get_authorization_header()


def get_base_authorization_header(base_token: str) -> Dict[str, str]:
    """
    获取使用用户授权码（PersonalBaseToken）的认证头。
    
    Args:
        base_token: 用户的个人授权码（PersonalBaseToken）
        
    Returns:
        包含 Authorization 头的字典
        
    Raises:
        ValueError: 当 base_token 为空时
    """
    if not base_token or base_token.strip() == '':
        raise ValueError("base_token 不能为空")
    
    return {
        "Authorization": f"Bearer {base_token.strip()}"
    }


def get_base_api_url(path: str) -> str:
    """获取完整的 Base API URL（主要用于多维表格 API）"""
    path = path.lstrip('/')
    return f"{BASE_API_DOMAIN.rstrip('/')}/{path}"


def get_open_api_url(path: str) -> str:
    """获取完整的 Open API URL（用于 Drive 等通用 API）"""
    path = path.lstrip('/')
    return f"{OPEN_API_DOMAIN.rstrip('/')}/{path}"
