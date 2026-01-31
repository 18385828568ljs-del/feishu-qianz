import logging
import os
import sys

from sqlalchemy import text

# 允许直接用 python 运行该脚本（而不要求从 backend/ 目录运行）
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from user_db_manager import (
    get_master_engine,
    ensure_user_database,
    get_user_session,
    init_master_database,
)  # noqa: E402
from database import UserProfile  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_QUOTA = int(os.getenv("DEFAULT_QUOTA", "20"))


def main():
    # 先确保主库存在（否则 get_master_engine() 连接会报 Unknown database 'feishu_master'）
    init_master_database()

    engine = get_master_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT user_key, open_id, tenant_key FROM user_databases")
        ).fetchall()

    if not rows:
        logger.warning("主库 user_databases 为空，没有可初始化的用户")
        return

    logger.info(f"将初始化 {len(rows)} 个用户的配额为 {DEFAULT_QUOTA}（强制覆盖）")

    ok_count = 0
    fail_count = 0

    for user_key, open_id, tenant_key in rows:
        try:
            ensure_user_database(user_key)
            user_db = get_user_session(user_key)
            try:
                profile = user_db.query(UserProfile).first()
                if not profile:
                    profile = UserProfile(
                        open_id=open_id,
                        tenant_key=tenant_key,
                        remaining_quota=DEFAULT_QUOTA,
                        total_used=0,
                        total_paid=0,
                    )
                    user_db.add(profile)
                    user_db.commit()
                else:
                    profile.open_id = open_id
                    profile.tenant_key = tenant_key
                    profile.remaining_quota = DEFAULT_QUOTA
                    user_db.commit()

                ok_count += 1

            finally:
                user_db.close()

        except Exception as e:
            fail_count += 1
            logger.exception(f"初始化失败 user_key={user_key}: {e}")

    logger.info(f"完成：成功 {ok_count}，失败 {fail_count}")


if __name__ == "__main__":
    main()
