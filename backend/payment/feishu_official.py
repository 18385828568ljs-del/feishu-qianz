"""
飞书官方付费能力 API 实现
注意: 当前暂时禁用飞书API调用，使用本地配额管理
待在飞书开放平台配置好付费能力后再启用
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class FeishuPaymentService:
    """飞书官方付费能力服务"""
    
    def __init__(self):
        # 使用现有的APP_ID和APP_SECRET环境变量
        self.app_id = os.getenv("APP_ID")
        self.app_secret = os.getenv("APP_SECRET")
        self.access_token = None
        self.base_url = "https://open.feishu.cn/open-apis"
    
    def check_user_paid_scope(self, open_id: str, tenant_key: str) -> Dict[str, Any]:
        """
        检查用户付费权益
        
        当前暂时禁用飞书API调用，直接降级到本地配额管理
        
        Args:
            open_id: 用户open_id
            tenant_key: 租户key
            
        Returns:
            {
                "has_permission": bool,
                "remaining_quota": int,
                "is_need_pay": bool,
                "use_local": bool  # 标记使用本地管理
            }
        """
        # 暂时完全禁用飞书API调用，直接使用本地配额管理
        # TODO: 在飞书开放平台配置好付费能力后，填写正确的API端点并启用
        return {
            "has_permission": True,
            "remaining_quota": 0,
            "is_need_pay": False,
            "use_local": True  # 标记使用本地管理
        }
    
    def consume_quota(self, open_id: str, tenant_key: str, count: int = 1) -> bool:
        """
        消耗用户配额
        
        当前暂时禁用，使用本地配额管理
        """
        # 暂时禁用飞书API调用，直接返回True让本地逻辑处理
        return True
    
    def get_marketplace_url(self) -> str:
        """
        获取插件市场购买链接
        
        Returns:
            str: 飞书插件市场详情页URL
        """
        return f"https://app.feishu.cn/app/{self.app_id}"


# 创建全局单例
feishu_payment_service = FeishuPaymentService()
