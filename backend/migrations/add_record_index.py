"""
数据库迁移脚本：为 sign_forms 表添加 record_index 字段
执行方式：python -m migrations.add_record_index
或者在应用启动时自动执行
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text


def migrate():
    """执行迁移：添加 record_index 字段"""
    db = SessionLocal()
    try:
        # 检查字段是否已存在
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'sign_forms'
            AND COLUMN_NAME = 'record_index'
        """))
        
        count = result.fetchone()[0]
        
        if count == 0:
            # 字段不存在，添加字段
            print("正在添加 record_index 字段...")
            db.execute(text("""
                ALTER TABLE `sign_forms` 
                ADD COLUMN `record_index` INT NOT NULL DEFAULT 1 
                COMMENT '记录条索引，默认为1（记录条1）' 
                AFTER `creator_refresh_token`
            """))
            db.commit()
            print("✅ record_index 字段添加成功！")
        else:
            print("ℹ️  record_index 字段已存在，跳过迁移")
            
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

