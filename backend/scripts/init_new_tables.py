"""
初始化新表结构
在 feishu_master 数据库中创建 app_user_identities 和 user_activities 表

执行方式：
cd backend
python scripts/init_new_tables.py
"""
import os
import sys
import logging

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from user_db_manager import init_master_database
from user_router import Base as UserRouterBase, AppUserIdentity, UserActivity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_tables():
    """初始化新表"""
    try:
        logger.info("=" * 60)
        logger.info("🚀 开始初始化新表结构")
        logger.info("=" * 60)
        
        # 1. 确保 feishu_master 数据库存在
        logger.info("📦 初始化主数据库...")
        init_master_database()
        
        # 2. 创建表结构
        from user_db_manager import get_master_engine
        engine = get_master_engine()
        
        logger.info("📋 创建表: app_user_identities")
        logger.info("📋 创建表: user_activities")
        
        UserRouterBase.metadata.create_all(bind=engine)
        
        logger.info("=" * 60)
        logger.info("✅ 表结构初始化完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("创建的表：")
        logger.info("  - app_user_identities (用户元信息)")
        logger.info("  - user_activities (用户活动日志)")
        logger.info("")
        logger.info("下一步：运行数据迁移脚本")
        logger.info("  python backend/scripts/migrate_users_to_new_schema.py")
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {str(e)}")
        raise


if __name__ == "__main__":
    init_tables()
