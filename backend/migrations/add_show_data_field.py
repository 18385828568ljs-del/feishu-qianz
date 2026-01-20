"""
数据库迁移脚本：为 sign_forms 表添加 show_data 字段
执行方式：python -m migrations.add_show_data_field
或者在应用启动时自动执行
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text


def migrate():
    """执行迁移：添加 show_data 字段"""
    db = SessionLocal()
    try:
        # 检查字段是否已存在
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'sign_forms'
            AND COLUMN_NAME = 'show_data'
        """))
        
        count = result.fetchone()[0]
        
        if count == 0:
            # 字段不存在，添加字段
            print("正在添加 show_data 字段...")
            db.execute(text("""
                ALTER TABLE `sign_forms` 
                ADD COLUMN `show_data` BOOLEAN NOT NULL DEFAULT FALSE 
                COMMENT '是否在表单中显示关联记录的数据' 
                AFTER `record_index`
            """))
            db.commit()
            print("[OK] show_data 字段添加成功！")
        else:
            print("[INFO] show_data 字段已存在，跳过迁移")
            
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

