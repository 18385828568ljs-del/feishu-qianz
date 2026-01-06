"""
Redis Session 存储模块
用于替代内存存储，支持多实例部署和服务重启后 session 保持
"""
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any

from dotenv import load_dotenv

load_dotenv()

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
SESSION_EXPIRE_SECONDS = int(os.getenv("SESSION_EXPIRE_SECONDS", "86400"))  # 默认24小时

# Redis 客户端
_redis_client = None
_fallback_mode = False


def get_redis_client():
    """获取 Redis 客户端（懒加载）"""
    global _redis_client, _fallback_mode
    
    if _fallback_mode:
        return None
        
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                db=REDIS_DB,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # 测试连接
            _redis_client.ping()
            print(f"[Redis] Connected to {REDIS_HOST}:{REDIS_PORT}")
        except ImportError:
            print("[Redis] redis package not installed, falling back to memory storage")
            _fallback_mode = True
            return None
        except Exception as e:
            print(f"[Redis] Connection failed: {e}, falling back to memory storage")
            _fallback_mode = True
            return None
    
    return _redis_client


# 内存回退存储（Redis 不可用时使用）
_memory_store: Dict[str, Dict[str, Any]] = {}


def _get_session_key(session_id: str) -> str:
    """生成 Redis key"""
    return f"feishu:session:{session_id}"


def set_session(session_id: str, data: Dict[str, Any]) -> bool:
    """
    存储 session 数据
    
    Args:
        session_id: 会话 ID
        data: session 数据，包含 access_token, refresh_token, expires_at, user 等
    
    Returns:
        是否存储成功
    """
    redis_client = get_redis_client()
    
    # 处理 datetime 对象
    serializable_data = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            serializable_data[key] = value.isoformat()
        else:
            serializable_data[key] = value
    
    if redis_client:
        try:
            key = _get_session_key(session_id)
            redis_client.setex(key, SESSION_EXPIRE_SECONDS, json.dumps(serializable_data))
            return True
        except Exception as e:
            print(f"[Redis] Set session failed: {e}")
            # 回退到内存存储
            _memory_store[session_id] = serializable_data
            return True
    else:
        # 使用内存存储
        _memory_store[session_id] = serializable_data
        return True


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    获取 session 数据
    
    Args:
        session_id: 会话 ID
    
    Returns:
        session 数据，不存在时返回 None
    """
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            key = _get_session_key(session_id)
            data = redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"[Redis] Get session failed: {e}")
            # 回退到内存存储
            return _memory_store.get(session_id)
    else:
        return _memory_store.get(session_id)


def delete_session(session_id: str) -> bool:
    """
    删除 session
    
    Args:
        session_id: 会话 ID
    
    Returns:
        是否删除成功
    """
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            key = _get_session_key(session_id)
            redis_client.delete(key)
            return True
        except Exception as e:
            print(f"[Redis] Delete session failed: {e}")
            _memory_store.pop(session_id, None)
            return True
    else:
        _memory_store.pop(session_id, None)
        return True


def session_exists(session_id: str) -> bool:
    """
    检查 session 是否存在
    
    Args:
        session_id: 会话 ID
    
    Returns:
        是否存在
    """
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            key = _get_session_key(session_id)
            return redis_client.exists(key) > 0
        except Exception as e:
            print(f"[Redis] Check session failed: {e}")
            return session_id in _memory_store
    else:
        return session_id in _memory_store


def update_session(session_id: str, updates: Dict[str, Any]) -> bool:
    """
    更新 session 中的部分字段
    
    Args:
        session_id: 会话 ID
        updates: 要更新的字段
    
    Returns:
        是否更新成功
    """
    data = get_session(session_id)
    if data is None:
        return False
    
    data.update(updates)
    return set_session(session_id, data)


def list_sessions(limit: int = 10) -> list:
    """
    列出最近的 session（用于调试）
    
    Args:
        limit: 最大返回数量
    
    Returns:
        session ID 列表
    """
    redis_client = get_redis_client()
    
    if redis_client:
        try:
            keys = redis_client.keys("feishu:session:*")
            return [k.replace("feishu:session:", "") for k in keys[:limit]]
        except Exception as e:
            print(f"[Redis] List sessions failed: {e}")
            return list(_memory_store.keys())[:limit]
    else:
        return list(_memory_store.keys())[:limit]


# ==================== 兼容性接口 ====================
# 提供类似 dict 的接口，方便替换原有的 USER_TOKENS

class SessionStore:
    """
    Session 存储类，提供类似 dict 的接口
    用于替换原有的 USER_TOKENS = {} 用法
    """
    
    def __getitem__(self, session_id: str) -> Dict[str, Any]:
        data = get_session(session_id)
        if data is None:
            raise KeyError(session_id)
        return data
    
    def __setitem__(self, session_id: str, value: Dict[str, Any]):
        set_session(session_id, value)
    
    def __contains__(self, session_id: str) -> bool:
        return session_exists(session_id)
    
    def __delitem__(self, session_id: str):
        delete_session(session_id)
    
    def get(self, session_id: str, default=None):
        data = get_session(session_id)
        return data if data is not None else default
    
    def keys(self):
        return list_sessions(100)
    
    def pop(self, session_id: str, default=None):
        data = get_session(session_id)
        if data is not None:
            delete_session(session_id)
            return data
        return default


# 导出兼容接口
USER_TOKENS = SessionStore()
