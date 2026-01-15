"""
Session 存储模块
优先使用 MySQL 数据库存储，Redis 作为可选的后备方案
如果都不可用，回退到内存存储（仅开发环境）
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from dotenv import load_dotenv

load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

# Session 过期时间配置
SESSION_EXPIRE_SECONDS = int(os.getenv("SESSION_EXPIRE_SECONDS", "86400"))  # 默认24小时

# 存储后端选择：mysql, redis, memory
# 优先级：如果配置了 REDIS_HOST 且可用 -> Redis，否则 -> MySQL，最后 -> 内存
SESSION_STORAGE_BACKEND = os.getenv("SESSION_STORAGE_BACKEND", "auto")  # auto, mysql, redis, memory

# MySQL 数据库可用性标记（延迟初始化）
_db_available = None
_db_initialized = False

# Redis 客户端（延迟初始化，可选）
_redis_client = None
_redis_available = None

# 内存存储（最后的后备方案）
_memory_store: Dict[str, Dict[str, Any]] = {}


def _check_db_available():
    """检查数据库是否可用（只检查一次）"""
    global _db_available, _db_initialized
    
    if _db_initialized:
        return _db_available
    
    _db_initialized = True
    try:
        from database import SessionLocal
        from sqlalchemy import text
        # 创建临时 session 测试连接
        test_session = SessionLocal()
        try:
            test_session.execute(text("SELECT 1"))
            _db_available = True
            logger.info("[Session] MySQL database is available for session storage")
        finally:
            test_session.close()
    except Exception as e:
        logger.warning(f"[Session] MySQL not available: {e}, will try other backends")
        _db_available = False
    
    return _db_available


def _get_db_session():
    """获取数据库会话（每次调用创建新的 session，确保线程安全）"""
    if not _check_db_available():
        return None
    
    try:
        from database import SessionLocal
        return SessionLocal()
    except Exception as e:
        logger.error(f"[Session] Failed to create database session: {e}")
        return None


def _get_redis_client():
    """获取 Redis 客户端（可选）"""
    global _redis_client, _redis_available
    
    # 如果明确禁用 Redis，直接返回 None
    if SESSION_STORAGE_BACKEND == "mysql" or SESSION_STORAGE_BACKEND == "memory":
        return None
    
    if _redis_available is False:
        return None
        
    if _redis_client is None:
        try:
            import redis
            REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
            REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
            REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
            REDIS_DB = int(os.getenv("REDIS_DB", "0"))
            
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
            _redis_available = True
            logger.info(f"[Session] Using Redis for session storage ({REDIS_HOST}:{REDIS_PORT})")
        except ImportError:
            logger.info("[Session] Redis package not installed, skipping Redis backend")
            _redis_available = False
            return None
        except Exception as e:
            logger.warning(f"[Session] Redis not available: {e}, will use MySQL instead")
            _redis_available = False
            return None
    
    # 检查连接是否仍然有效
    try:
        _redis_client.ping()
    except Exception as e:
        logger.warning(f"[Session] Redis connection lost: {e}, falling back to MySQL")
        _redis_client = None
        _redis_available = False
        return None
    
    return _redis_client


def _determine_backend():
    """确定使用哪个存储后端"""
    if SESSION_STORAGE_BACKEND == "memory":
        return "memory"
    elif SESSION_STORAGE_BACKEND == "redis":
        if _get_redis_client():
            return "redis"
        else:
            return "mysql" if _check_db_available() else "memory"
    elif SESSION_STORAGE_BACKEND == "mysql":
        return "mysql" if _check_db_available() else "memory"
    else:  # auto
        # 优先级：Redis（如果配置且可用） -> MySQL -> 内存
        if _get_redis_client():
            return "redis"
        elif _check_db_available():
            return "mysql"
        else:
            return "memory"


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
    backend = _determine_backend()
    
    # 处理 datetime 对象
    serializable_data = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            serializable_data[key] = value.isoformat()
        else:
            serializable_data[key] = value
    
    # 计算过期时间：优先使用 token 的实际过期时间，否则使用默认的 SESSION_EXPIRE_SECONDS
    if "expires_at" in data and isinstance(data["expires_at"], (int, float)):
        # expires_at 是时间戳（秒）
        expires_at = datetime.utcfromtimestamp(data["expires_at"])
        logger.debug(f"[Session] Using token expires_at: {expires_at} for session {session_id}")
    else:
        # 使用默认的过期时间
        expires_at = datetime.utcnow() + timedelta(seconds=SESSION_EXPIRE_SECONDS)
        logger.debug(f"[Session] Using default expires_at: {expires_at} for session {session_id}")
    
    try:
        if backend == "redis":
            redis_client = _get_redis_client()
            if redis_client:
                key = _get_session_key(session_id)
                redis_client.setex(key, SESSION_EXPIRE_SECONDS, json.dumps(serializable_data))
                return True
        
        elif backend == "mysql":
            db = _get_db_session()
            if db:
                try:
                    from database import OAuthSession
                    # 先尝试更新，如果不存在则插入
                    session = db.query(OAuthSession).filter(OAuthSession.session_id == session_id).first()
                    if session:
                        session.session_data = json.dumps(serializable_data)
                        session.expires_at = expires_at
                        session.updated_at = datetime.utcnow()
                        logger.info(f"[Session] Updating existing session {session_id} in MySQL, expires_at={expires_at}")
                    else:
                        session = OAuthSession(
                            session_id=session_id,
                            session_data=json.dumps(serializable_data),
                            expires_at=expires_at
                        )
                        db.add(session)
                        logger.info(f"[Session] Inserting new session {session_id} into MySQL, expires_at={expires_at}")
                    db.commit()
                    logger.info(f"[Session] MySQL commit successful for session {session_id}")
                    return True
                except Exception as e:
                    db.rollback()
                    logger.error(f"[Session] MySQL set_session error for {session_id}: {e}", exc_info=True)
                    # 不抛出异常，而是回退到内存存储
                    logger.warning(f"[Session] Falling back to memory storage for session {session_id}")
                    _memory_store[session_id] = serializable_data
                    return True
                finally:
                    db.close()
            else:
                logger.warning(f"[Session] MySQL db session is None, falling back to memory storage for session {session_id}")
        
        # 回退到内存存储
        _memory_store[session_id] = serializable_data
        if backend != "memory":
            logger.info(f"[Session] Using memory storage as fallback (backend: {backend}) for session {session_id}")
        return True
        
    except Exception as e:
        logger.error(f"[Session] Set session failed ({backend}): {e}", exc_info=True)
        # 回退到内存存储
        _memory_store[session_id] = serializable_data
        return True


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    获取 session 数据
    
    Args:
        session_id: 会话 ID
    
    Returns:
        session 数据，不存在或已过期时返回 None
    """
    backend = _determine_backend()
    
    try:
        if backend == "redis":
            redis_client = _get_redis_client()
            if redis_client:
                key = _get_session_key(session_id)
                data = redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
        
        elif backend == "mysql":
            db = _get_db_session()
            if db:
                try:
                    from database import OAuthSession
                    session = db.query(OAuthSession).filter(
                        OAuthSession.session_id == session_id,
                        OAuthSession.expires_at > datetime.utcnow()
                    ).first()
                    if session:
                        logger.debug(f"[Session] Session {session_id} found in MySQL")
                        return json.loads(session.session_data)
                    # MySQL 中没找到，检查内存存储（可能存储时回退到了内存）
                    memory_data = _memory_store.get(session_id)
                    if memory_data:
                        logger.info(f"[Session] Session {session_id} found in memory storage (MySQL query returned None)")
                    else:
                        logger.debug(f"[Session] Session {session_id} not found in MySQL or memory")
                    return memory_data
                finally:
                    db.close()
        
        # 内存存储
        return _memory_store.get(session_id)
        
    except Exception as e:
        logger.error(f"[Session] Get session failed ({backend}): {e}", exc_info=True)
        # 异常时回退到内存存储
        memory_data = _memory_store.get(session_id)
        if memory_data:
            logger.info(f"[Session] Session {session_id} found in memory storage after exception")
        return memory_data


def delete_session(session_id: str) -> bool:
    """
    删除 session
    
    Args:
        session_id: 会话 ID
    
    Returns:
        是否删除成功
    """
    backend = _determine_backend()
    
    try:
        if backend == "redis":
            redis_client = _get_redis_client()
            if redis_client:
                key = _get_session_key(session_id)
                redis_client.delete(key)
                return True
        
        elif backend == "mysql":
            db = _get_db_session()
            if db:
                try:
                    from database import OAuthSession
                    db.query(OAuthSession).filter(OAuthSession.session_id == session_id).delete()
                    db.commit()
                    return True
                except Exception as e:
                    db.rollback()
                    logger.error(f"[Session] MySQL delete_session error: {e}", exc_info=True)
                    raise
                finally:
                    db.close()
        
        # 内存存储
        _memory_store.pop(session_id, None)
        return True
        
    except Exception as e:
        print(f"[Session] Delete session failed ({backend}): {e}")
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
    backend = _determine_backend()
    
    try:
        if backend == "redis":
            redis_client = _get_redis_client()
            if redis_client:
                key = _get_session_key(session_id)
                return redis_client.exists(key) > 0
        
        elif backend == "mysql":
            db = _get_db_session()
            if db:
                try:
                    from database import OAuthSession
                    exists = db.query(OAuthSession).filter(
                        OAuthSession.session_id == session_id,
                        OAuthSession.expires_at > datetime.utcnow()
                    ).first() is not None
                    if exists:
                        return True
                    # MySQL 中没找到，检查内存存储
                    return session_id in _memory_store
                finally:
                    db.close()
        
        # 内存存储
        return session_id in _memory_store
        
    except Exception as e:
        logger.error(f"[Session] Check session failed ({backend}): {e}", exc_info=True)
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
    backend = _determine_backend()
    
    try:
        if backend == "redis":
            redis_client = _get_redis_client()
            if redis_client:
                keys = redis_client.keys("feishu:session:*")
                return [k.replace("feishu:session:", "") for k in keys[:limit]]
        
        elif backend == "mysql":
            db = _get_db_session()
            if db:
                try:
                    from database import OAuthSession
                    sessions = db.query(OAuthSession).filter(
                        OAuthSession.expires_at > datetime.utcnow()
                    ).order_by(OAuthSession.created_at.desc()).limit(limit).all()
                    return [s.session_id for s in sessions]
                finally:
                    db.close()
        
        # 内存存储
        return list(_memory_store.keys())[:limit]
        
    except Exception as e:
        print(f"[Session] List sessions failed ({backend}): {e}")
        return list(_memory_store.keys())[:limit]


def cleanup_expired_sessions():
    """清理过期的 session（仅 MySQL 需要，Redis 会自动过期）"""
    db = _get_db_session()
    if db:
        try:
            from database import OAuthSession
            deleted = db.query(OAuthSession).filter(
                OAuthSession.expires_at <= datetime.utcnow()
            ).delete()
            db.commit()
            if deleted > 0:
                logger.info(f"[Session] Cleaned up {deleted} expired sessions")
        except Exception as e:
            db.rollback()
            logger.error(f"[Session] Cleanup expired sessions failed: {e}", exc_info=True)
        finally:
            db.close()


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
