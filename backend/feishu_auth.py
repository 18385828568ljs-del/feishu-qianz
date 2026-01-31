"""
Feishu Server-side Authentication Service
Handles tenant_access_token management for server-to-server API calls.
"""
import os
import time
import logging
from typing import Optional, Dict, Any
import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# 从环境变量获取飞书应用凭证
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
FEISHU_API_BASE = os.getenv("FEISHU_API_BASE", "https://open.feishu.cn")

class FeishuAuthService:
    _instance = None
    _token_info = {
        "tenant_access_token": "",
        "expire": 0,
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FeishuAuthService, cls).__new__(cls)
            # 初始化时检查必要配置（仅警告，不强制要求）
            # 对于多维表格插件，使用用户的PersonalBaseToken，不需要应用凭证
            if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
                logger.warning("FEISHU_APP_ID or FEISHU_APP_SECRET not configured - tenant_access_token will not be available")
        return cls._instance

    def get_tenant_access_token(self) -> str:
        """获取有效的 tenant_access_token，自动处理刷新"""
        if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
            raise RuntimeError("飞书应用凭证未配置，无法获取tenant_access_token。多维表格插件请使用用户的PersonalBaseToken。")
        
        now = int(time.time())
        
        # 如果 token 未过期，直接返回缓存的 token
        if self._token_info["expire"] > now + 60:  # 提前1分钟刷新
            return self._token_info["tenant_access_token"]
        
        # 否则获取新 token
        return self._refresh_tenant_access_token()

    def _refresh_tenant_access_token(self) -> str:
        """从飞书服务器获取新的 tenant_access_token"""
        url = f"{FEISHU_API_BASE}/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET,
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get tenant_access_token: {result.get('msg')}"
                )
            
            # 更新 token 信息（提前5分钟过期）
            self._token_info = {
                "tenant_access_token": result["tenant_access_token"],
                "expire": int(time.time()) + result["expire"] - 300,
            }
            
            logger.info("Refreshed tenant_access_token")
            return self._token_info["tenant_access_token"]
            
        except requests.RequestException as e:
            logger.error(f"Failed to refresh tenant_access_token: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to Feishu auth service: {str(e)}"
            )

    def get_authorization_header(self) -> Dict[str, str]:
        """获取包含 Authorization 头的字典"""
        return {"Authorization": f"Bearer {self.get_tenant_access_token()}"}


# 全局单例实例
feishu_auth = FeishuAuthService()


def get_feishu_auth_headers() -> Dict[str, str]:
    """获取包含 Feishu 认证头的字典（兼容旧代码）"""
    return feishu_auth.get_authorization_header()
