import logging
import os
import sys

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 允许直接用 python 运行该脚本（而不要求从 backend/ 目录运行）
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 加载 .env 文件，这样 MYSQL_PASSWORD 等环境变量才能被读取
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 共享库名称来自环境变量（database.py 默认 feishu）
SHARED_DB_NAME = os.getenv("MYSQL_DATABASE", "feishu")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

TABLES_TO_TRUNCATE = [
    "orders",
    "signature_logs",
    "sign_forms",
    "invite_codes",
]


def main():
    url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{SHARED_DB_NAME}?charset=utf8mb4"
    engine = create_engine(url, pool_pre_ping=True, echo=False)

    logger.warning(
        "将清空共享库 %s 的表：%s（不可恢复）",
        SHARED_DB_NAME,
        ", ".join(TABLES_TO_TRUNCATE),
    )

    with engine.connect() as conn:
        # TRUNCATE 可能受外键限制；先关闭外键检查
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in TABLES_TO_TRUNCATE:
            try:
                conn.execute(text(f"TRUNCATE TABLE `{table}`"))
                logger.info("已清空表 %s.%s", SHARED_DB_NAME, table)
            except Exception as e:
                # 如果表不存在，也视为成功，继续执行
                if "Unknown table" in str(e) or "doesn't exist" in str(e):
                    logger.warning("表 %s.%s 不存在，跳过清理。", SHARED_DB_NAME, table)
                else:
                    raise e
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        conn.commit()

    logger.info("清理完成：已保留 users / pricing_plans 等其它表")


if __name__ == "__main__":
    main()
