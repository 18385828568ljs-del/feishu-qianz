"""
数据迁移脚本：从旧的 users 表迁移到新架构
- 旧架构：users 表（共享库）
- 新架构：app_user_identities 表（主库） + user_profile 表（用户独立数据库）

执行方式：
cd backend
python scripts/migrate_users_to_new_schema.py
"""
import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到 Python 路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import User, UserProfile
from user_router import AppUserIdentity
from user_db_manager import ensure_user_database, get_user_session, get_master_engine
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_shared_db_session():
    """获取共享数据库会话（旧的 users 表所在的库）"""
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "feishu")
    
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def migrate_users():
    """迁移用户数据"""
    shared_db = get_shared_db_session()
    master_engine = get_master_engine()
    MasterSession = sessionmaker(bind=master_engine)
    master_db = MasterSession()
    
    try:
        # 1. 检查旧表是否存在
        result = shared_db.execute(text("SHOW TABLES LIKE 'users'"))
        if not result.fetchone():
            logger.warning("❌ 旧的 users 表不存在，无需迁移")
            return
        
        # 2. 查询所有旧用户
        old_users = shared_db.query(User).all()
        logger.info(f"📊 找到 {len(old_users)} 个旧用户需要迁移")
        
        if len(old_users) == 0:
            logger.info("✅ 没有用户需要迁移")
            return
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for old_user in old_users:
            try:
                # 3. 检查是否已经迁移过
                existing = master_db.query(AppUserIdentity).filter(
                    AppUserIdentity.feishu_user_id == old_user.open_id,
                    AppUserIdentity.tenant_key == old_user.tenant_key
                ).first()
                
                if existing:
                    logger.info(f"⏭️  跳过已存在用户: {old_user.open_id}")
                    skipped_count += 1
                    continue
                
                # 4. 创建新的用户元信息记录
                new_user = AppUserIdentity(
                    feishu_user_id=old_user.open_id,
                    tenant_key=old_user.tenant_key,
                    fingerprint_hash=None,  # 旧数据没有指纹
                    created_at=old_user.created_at,
                    last_seen_at=old_user.updated_at or old_user.created_at
                )
                master_db.add(new_user)
                master_db.flush()
                
                logger.info(f"✅ 创建用户元信息: {old_user.open_id} (ID: {new_user.id})")
                
                # 5. 创建用户独立数据库并迁移配额数据
                user_key = f"{old_user.open_id}::{old_user.tenant_key}"
                ensure_user_database(user_key)
                user_db = get_user_session(user_key)
                
                try:
                    # 检查是否已有配置
                    existing_profile = user_db.query(UserProfile).first()
                    if existing_profile:
                        logger.info(f"⏭️  用户配置已存在: {user_key}")
                    else:
                        # 创建用户配置
                        profile = UserProfile(
                            open_id=old_user.open_id,
                            tenant_key=old_user.tenant_key,
                            remaining_quota=old_user.remaining_quota or 20,
                            total_used=old_user.total_used or 0,
                            current_plan_id=old_user.current_plan_id,
                            plan_expires_at=old_user.plan_expires_at,
                            plan_quota_reset_at=old_user.plan_quota_reset_at,
                            is_unlimited=old_user.is_unlimited or False,
                            invite_code_used=old_user.invite_code_used,
                            invite_expire_at=old_user.invite_expire_at,
                            total_paid=old_user.total_paid or 0,
                            created_at=old_user.created_at,
                            updated_at=old_user.updated_at or old_user.created_at
                        )
                        user_db.add(profile)
                        user_db.commit()
                        logger.info(f"✅ 创建用户配置: {user_key} (配额: {profile.remaining_quota})")
                finally:
                    user_db.close()
                
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"❌ 迁移用户失败 {old_user.open_id}: {str(e)}")
                error_count += 1
                master_db.rollback()
                continue
        
        # 6. 提交主库的更改
        master_db.commit()
        
        # 7. 输出统计
        logger.info("=" * 60)
        logger.info("📊 迁移统计:")
        logger.info(f"   总用户数: {len(old_users)}")
        logger.info(f"   ✅ 成功迁移: {migrated_count}")
        logger.info(f"   ⏭️  跳过已存在: {skipped_count}")
        logger.info(f"   ❌ 迁移失败: {error_count}")
        logger.info("=" * 60)
        
        if migrated_count > 0:
            logger.info("✅ 数据迁移完成！")
            logger.info("")
            logger.info("⚠️  注意事项：")
            logger.info("1. 请测试管理后台功能是否正常")
            logger.info("2. 确认无误后，可以删除旧的 users 表")
            logger.info("3. 删除命令: DROP TABLE IF EXISTS users;")
        
    except Exception as e:
        logger.error(f"❌ 迁移过程出错: {str(e)}")
        master_db.rollback()
        raise
    finally:
        shared_db.close()
        master_db.close()


def verify_migration():
    """验证迁移结果"""
    shared_db = get_shared_db_session()
    master_engine = get_master_engine()
    MasterSession = sessionmaker(bind=master_engine)
    master_db = MasterSession()
    
    try:
        old_count = shared_db.query(User).count()
        new_count = master_db.query(AppUserIdentity).count()
        
        logger.info("=" * 60)
        logger.info("🔍 验证迁移结果:")
        logger.info(f"   旧表 (users) 用户数: {old_count}")
        logger.info(f"   新表 (app_user_identities) 用户数: {new_count}")
        
        if new_count >= old_count:
            logger.info("✅ 迁移验证通过！")
        else:
            logger.warning(f"⚠️  新表用户数少于旧表，可能有用户未迁移")
        
        logger.info("=" * 60)
        
    finally:
        shared_db.close()
        master_db.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 开始用户数据迁移")
    logger.info("=" * 60)
    
    try:
        migrate_users()
        verify_migration()
        
        logger.info("")
        logger.info("✅ 迁移脚本执行完成！")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {str(e)}")
        sys.exit(1)
