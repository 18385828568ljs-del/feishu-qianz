"""
用户数据库管理模块
实现每用户独立数据库的动态创建和连接
"""
import os
import hashlib
import logging
from typing import Optional, Dict
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

load_dotenv()
logger = logging.getLogger(__name__)

# 数据库连接配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MASTER_DB_NAME = "feishu_master"

# 缓存用户数据库引擎，避免重复创建
_user_engines: Dict[str, Engine] = {}
_user_session_factories: Dict[str, sessionmaker] = {}


def get_user_db_name(user_key: str) -> str:
    """
    根据 user_key 生成用户数据库名称
    
    Args:
        user_key: 用户唯一标识，格式为 open_id::tenant_key
    
    Returns:
        数据库名称，格式为 feishu_user_<hash前8位>
    """
    hash_value = hashlib.md5(user_key.encode()).hexdigest()[:8]
    return f"feishu_user_{hash_value}"


def get_master_engine() -> Engine:
    """获取主数据库引擎"""
    url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MASTER_DB_NAME}?charset=utf8mb4"
    return create_engine(url, pool_pre_ping=True, echo=False)


def get_user_engine(user_key: str) -> Engine:
    """
    获取用户数据库引擎（带缓存）
    
    Args:
        user_key: 用户唯一标识
    
    Returns:
        SQLAlchemy Engine 实例
    """
    if user_key in _user_engines:
        return _user_engines[user_key]
    
    db_name = get_user_db_name(user_key)
    url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{db_name}?charset=utf8mb4"
    engine = create_engine(url, pool_pre_ping=True, echo=False, pool_size=5, max_overflow=10)
    _user_engines[user_key] = engine
    return engine


def get_user_session(user_key: str) -> Session:
    """
    获取用户数据库会话
    
    Args:
        user_key: 用户唯一标识
    
    Returns:
        SQLAlchemy Session 实例
    """
    if user_key not in _user_session_factories:
        engine = get_user_engine(user_key)
        _user_session_factories[user_key] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return _user_session_factories[user_key]()


def get_master_session() -> Session:
    """获取主数据库会话"""
    engine = get_master_engine()
    SessionMaster = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionMaster()


def create_user_database(user_key: str) -> bool:
    """
    为用户创建独立数据库并初始化表结构
    
    Args:
        user_key: 用户唯一标识
    
    Returns:
        是否创建成功
    """
    db_name = get_user_db_name(user_key)
    
    # 连接不指定数据库的 MySQL 服务
    server_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/?charset=utf8mb4"
    server_engine = create_engine(server_url, echo=False)
    
    try:
        with server_engine.connect() as conn:
            # 检查数据库是否已存在
            result = conn.execute(text(f"SHOW DATABASES LIKE '{db_name}'"))
            if result.fetchone():
                logger.info(f"用户数据库已存在: {db_name}")
                return True
            
            # 创建数据库
            conn.execute(text(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
            logger.info(f"成功创建用户数据库: {db_name}")
        
        # 初始化表结构
        _init_user_tables(user_key)
        
        # 在主库中记录用户数据库信息
        _register_user_database(user_key, db_name)
        
        return True
    except Exception as e:
        logger.error(f"创建用户数据库失败: {e}")
        return False
    finally:
        server_engine.dispose()


def _init_user_tables(user_key: str):
    """初始化用户数据库表结构"""
    from database import UserBase  # 导入用户库专用的 Base
    
    engine = get_user_engine(user_key)
    UserBase.metadata.create_all(bind=engine)
    logger.info(f"用户数据库表结构初始化完成: {get_user_db_name(user_key)}")


def _register_user_database(user_key: str, db_name: str):
    """在主库中注册用户数据库信息"""
    try:
        master_engine = get_master_engine()
        with master_engine.connect() as conn:
            # 解析 user_key
            parts = user_key.split("::")
            open_id = parts[0] if len(parts) > 0 else ""
            tenant_key = parts[1] if len(parts) > 1 else ""
            
            # 检查是否已注册
            result = conn.execute(
                text("SELECT id FROM user_databases WHERE user_key = :user_key"),
                {"user_key": user_key}
            )
            if result.fetchone():
                # 已注册，更新最后活跃时间
                conn.execute(
                    text("UPDATE user_databases SET last_active_at = NOW() WHERE user_key = :user_key"),
                    {"user_key": user_key}
                )
            else:
                # 新注册
                conn.execute(
                    text("""
                        INSERT INTO user_databases (user_key, open_id, tenant_key, db_name, db_created, created_at, last_active_at)
                        VALUES (:user_key, :open_id, :tenant_key, :db_name, TRUE, NOW(), NOW())
                    """),
                    {"user_key": user_key, "open_id": open_id, "tenant_key": tenant_key, "db_name": db_name}
                )
            conn.commit()
    except Exception as e:
        logger.warning(f"注册用户数据库信息失败: {e}")


def ensure_user_database(user_key: str) -> bool:
    """
    确保用户数据库存在，如果不存在则创建
    
    Args:
        user_key: 用户唯一标识
    
    Returns:
        数据库是否可用
    """
    db_name = get_user_db_name(user_key)
    
    # 快速检查：尝试连接
    try:
        engine = get_user_engine(user_key)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        # 数据库不存在，创建它
        return create_user_database(user_key)


def init_master_database():
    """初始化主数据库（仅需运行一次）"""
    server_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/?charset=utf8mb4"
    server_engine = create_engine(server_url, echo=False)
    
    try:
        with server_engine.connect() as conn:
            # 创建主数据库
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{MASTER_DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        
        # 创建主库表结构
        master_engine = get_master_engine()
        with master_engine.connect() as conn:
            # 用户数据库注册表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_databases (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_key VARCHAR(256) UNIQUE NOT NULL,
                    open_id VARCHAR(128) NOT NULL,
                    tenant_key VARCHAR(128) NOT NULL,
                    db_name VARCHAR(64) NOT NULL,
                    db_created BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT NOW(),
                    last_active_at DATETIME,
                    INDEX idx_open_id (open_id),
                    INDEX idx_tenant_key (tenant_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            
            # 全局套餐定价表（从旧库迁移）
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pricing_plans (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    plan_id VARCHAR(32) UNIQUE NOT NULL,
                    name VARCHAR(64) NOT NULL,
                    quota_count INT,
                    price INT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    sort_order INT DEFAULT 0,
                    description VARCHAR(256),
                    billing_type VARCHAR(16) DEFAULT 'monthly',
                    monthly_price INT,
                    yearly_price INT,
                    unlimited BOOLEAN DEFAULT FALSE,
                    save_percent INT,
                    created_at DATETIME DEFAULT NOW(),
                    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
                    INDEX idx_plan_id (plan_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            conn.commit()
        
        logger.info("主数据库初始化完成")
        return True
    except Exception as e:
        logger.error(f"主数据库初始化失败: {e}")
        return False
    finally:
        server_engine.dispose()


if __name__ == "__main__":
    # 直接运行可初始化主数据库
    logging.basicConfig(level=logging.INFO)
    init_master_database()
    print("主数据库初始化完成!")
