"""
统一的用户标识模块
提供一致的用户识别和管理
"""
import hashlib
from dataclasses import dataclass
from typing import Optional


@dataclass
class UserIdentity:
    """
    统一的用户标识类
    
    用于在整个系统中一致地识别和管理用户
    """
    open_id: str
    tenant_key: str
    user_id: Optional[int] = None  # 数据库ID（来自 app_user_identities 表）
    
    def __post_init__(self):
        """验证必填字段"""
        if not self.open_id or not self.tenant_key:
            raise ValueError("open_id 和 tenant_key 不能为空")
    
    @property
    def user_key(self) -> str:
        """
        生成用户唯一标识
        格式: open_id::tenant_key
        """
        return f"{self.open_id}::{self.tenant_key}"
    
    @property
    def db_name(self) -> str:
        """
        生成用户数据库名称
        格式: feishu_user_<hash前8位>
        """
        hash_value = hashlib.md5(self.user_key.encode()).hexdigest()[:8]
        return f"feishu_user_{hash_value}"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'open_id': self.open_id,
            'tenant_key': self.tenant_key,
            'user_id': self.user_id,
            'user_key': self.user_key,
            'db_name': self.db_name
        }
    
    def to_jwt_payload(self) -> dict:
        """转换为 JWT payload"""
        if not self.user_id:
            raise ValueError("user_id 不能为空")
        
        return {
            'sub': str(self.user_id),
            'open_id': self.open_id,
            'tenant_key': self.tenant_key
        }
    
    @classmethod
    def from_jwt_payload(cls, payload: dict) -> 'UserIdentity':
        """从 JWT payload 创建"""
        return cls(
            open_id=payload.get('open_id'),
            tenant_key=payload.get('tenant_key'),
            user_id=int(payload.get('sub')) if payload.get('sub') else None
        )
    
    @classmethod
    def from_user_info(cls, user_info: dict) -> 'UserIdentity':
        """从 user_info 字典创建"""
        return cls(
            open_id=user_info.get('open_id'),
            tenant_key=user_info.get('tenant_key'),
            user_id=user_info.get('user_id')
        )
    
    @classmethod
    def from_feishu_response(cls, open_id: str, tenant_key: str) -> 'UserIdentity':
        """从飞书 API 响应创建"""
        return cls(
            open_id=open_id,
            tenant_key=tenant_key
        )
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"UserIdentity(open_id={self.open_id[:8]}***, tenant_key={self.tenant_key[:8]}***)"
    
    def __repr__(self) -> str:
        """调试表示"""
        return f"UserIdentity(open_id='{self.open_id}', tenant_key='{self.tenant_key}', user_id={self.user_id})"
    
    def __eq__(self, other) -> bool:
        """相等比较"""
        if not isinstance(other, UserIdentity):
            return False
        return self.user_key == other.user_key
    
    def __hash__(self) -> int:
        """哈希值"""
        return hash(self.user_key)
