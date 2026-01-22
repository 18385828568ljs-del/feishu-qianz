import logging
import os
import sys

from sqlalchemy import create_engine, text

# 允许直接用 python 运行该脚本（而不要求从 backend/ 目录运行）
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from user_db_manager import init_master_database, get_master_engine, get_user_db_name  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 旧共享库名称来自环境变量（database.py 里默认 feishu）
SHARED_DB_NAME = os.getenv("MYSQL_DATABASE", "feishu")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")


def main():
    init_master_database()

    shared_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{SHARED_DB_NAME}?charset=utf8mb4"
    shared_engine = create_engine(shared_url, pool_pre_ping=True, echo=False)

    with shared_engine.connect() as conn:
        # 从旧 users 表拉取用户
        rows = conn.execute(
            text("SELECT DISTINCT user_key, open_id, tenant_key FROM users")
        ).fetchall()

    if not rows:
        logger.warning(f"共享库 {SHARED_DB_NAME}.users 为空，没有可同步的用户")
        return

    master_engine = get_master_engine()
    inserted = 0
    updated = 0

    with master_engine.connect() as conn:
        for user_key, open_id, tenant_key in rows:
            db_name = get_user_db_name(user_key)

            # upsert（MySQL）
            res = conn.execute(
                text(
                    """
                    INSERT INTO user_databases (user_key, open_id, tenant_key, db_name, db_created, created_at, last_active_at)
                    VALUES (:user_key, :open_id, :tenant_key, :db_name, FALSE, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        open_id = VALUES(open_id),
                        tenant_key = VALUES(tenant_key),
                        db_name = VALUES(db_name),
                        last_active_at = NOW()
                    """
                ),
                {
                    "user_key": user_key,
                    "open_id": open_id,
                    "tenant_key": tenant_key,
                    "db_name": db_name,
                },
            )

            # rowcount 在不同驱动上可能不精确，这里只做粗略统计
            if res.rowcount == 1:
                inserted += 1
            else:
                updated += 1

        conn.commit()

    logger.info(f"同步完成：插入约 {inserted} 条，更新约 {updated} 条（总用户 {len(rows)}）")


if __name__ == "__main__":
    main()

