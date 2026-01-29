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
        base_token: 用户提供的授权码（必需）
    
    Returns:
        包含 Authorization 头的字典
    
    Raises:
        ValueError: 如果未提供授权码
    """
    if not base_token:
        # 不再使用全局默认 Token，强制要求用户提供授权码
        logger.error("No PersonalBaseToken provided - user authorization required")
        raise ValueError("未提供授权码，请先配置您的飞书授权码")
    return {"Authorization": f"Bearer {base_token}"}


def get_base_api_url(path: str) -> str:
    """获取完整的 Base API URL（用于多维表格API）"""
    path = path.lstrip('/')
    return f"{BASE_API_DOMAIN.rstrip('/')}/{path}"

def get_open_api_url(path: str) -> str:
    """获取完整的 Open API URL（用于Drive等通用API）"""
    path = path.lstrip('/')
    # Drive API 必须使用 open.feishu.cn 域名
    open_domain = "https://open.feishu.cn"
    return f"{open_domain}/{path}"


import requests

def ensure_signature_folder(headers: dict, folder_name: str = "数签助手_签名存档") -> Optional[str]:
    """
    确保存在指定名称的文件夹，并返回其 token。
    
    逻辑：
    1. 在根目录搜索该文件夹
    2. 如果存在，返回 token
    3. 如果不存在，创建该文件夹并返回 token
    """
    try:
        # 1. 搜索文件夹 (列出根目录下的文件)
        # 注意：这里简单列出根目录前50个文件，如果根目录文件太多可能会漏掉，但对于普通用户够用
        # 也可以使用高级搜索 API，但 PersonalBaseToken 权限可能受限
        # 搜索 API: POST /open-apis/drive/v1/files/search (目前用 List Children 代替)
        list_url = get_open_api_url("/open-apis/drive/v1/files?folder_token=root&page_size=50")
        r = requests.get(list_url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 0:
                files = data.get("data", {}).get("files", [])
                for f in files:
                    # 检查名字和类型 (mime_type: "application/vnd.feishu.folder")
                    if f.get("name") == folder_name and f.get("type") == "folder":
                        logger.info(f"Found existing folder: {folder_name} ({f.get('token')})")
                        return f.get("token")
        
        # 2. 如果没找到，创建文件夹
        create_url = get_open_api_url("/open-apis/drive/v1/files/create_folder")
        payload = {
            "name": folder_name,
            "folder_token": "root"
        }
        r = requests.post(create_url, json=payload, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if data.get("code") == 0:
                new_token = data.get("data", {}).get("token")
                logger.info(f"Created new folder: {folder_name} ({new_token})")
                return new_token
            else:
                logger.error(f"Failed to create folder: {data}")
        
    except Exception as e:
        logger.error(f"Error in ensure_signature_folder: {e}")
    
    return None
