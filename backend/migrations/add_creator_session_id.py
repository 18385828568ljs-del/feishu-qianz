"""
数据库迁移脚本：为 sign_forms 表添加 creator_session_id 字段
用于从 USER_TOKENS 获取最新的 refresh_token，避免使用已被刷新过的旧 token
执行方式：python -m migrations.add_creator_session_id
或者在应用启动时自动执行
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text


def migrate():
    """执行迁移：添加 creator_session_id 字段"""
    db = SessionLocal()
    try:
        # 检查字段是否已存在
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'sign_forms'
            AND COLUMN_NAME = 'creator_session_id'
        """))
        
        count = result.fetchone()[0]
        
        if count == 0:
            # 字段不存在，添加字段
            print("正在添加 creator_session_id 字段...")
            db.execute(text("""
                ALTER TABLE `sign_forms` 
                ADD COLUMN `creator_session_id` VARCHAR(64) NULL 
                COMMENT '创建者的 session_id（用于从 USER_TOKENS 获取最新的 refresh_token）' 
                AFTER `created_by`
            """))
            db.commit()
            print("[OK] creator_session_id 字段添加成功！")
        else:
            print("[INFO] creator_session_id 字段已存在，跳过迁移")
            
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

