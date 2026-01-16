"""
数据库迁移脚本：为 users 表添加套餐订阅相关字段
执行方式：python -m migrations.add_user_subscription_fields
或者在应用启动时自动执行
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text


def migrate():
    """执行迁移：添加用户套餐订阅相关字段"""
    db = SessionLocal()
    try:
        # 检查并添加 current_plan_id 字段
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'users'
            AND COLUMN_NAME = 'current_plan_id'
        """))
        count = result.fetchone()[0]
        if count == 0:
            print("正在添加 current_plan_id 字段...")
            db.execute(text("""
                ALTER TABLE `users` 
                ADD COLUMN `current_plan_id` VARCHAR(32) NULL 
                COMMENT '当前套餐ID（如 basic_monthly）' 
                AFTER `total_used`
            """))
            db.commit()
            print("✅ current_plan_id 字段添加成功！")
        else:
            print("ℹ️  current_plan_id 字段已存在，跳过")
        
        # 检查并添加 plan_expires_at 字段
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'users'
            AND COLUMN_NAME = 'plan_expires_at'
        """))
        count = result.fetchone()[0]
        if count == 0:
            print("正在添加 plan_expires_at 字段...")
            db.execute(text("""
                ALTER TABLE `users` 
                ADD COLUMN `plan_expires_at` DATETIME NULL 
                COMMENT '套餐到期时间' 
                AFTER `current_plan_id`
            """))
            db.commit()
            print("✅ plan_expires_at 字段添加成功！")
        else:
            print("ℹ️  plan_expires_at 字段已存在，跳过")
        
        # 检查并添加 plan_quota_reset_at 字段
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'users'
            AND COLUMN_NAME = 'plan_quota_reset_at'
        """))
        count = result.fetchone()[0]
        if count == 0:
            print("正在添加 plan_quota_reset_at 字段...")
            db.execute(text("""
                ALTER TABLE `users` 
                ADD COLUMN `plan_quota_reset_at` DATETIME NULL 
                COMMENT '配额重置时间（月付每月重置，年付每年重置）' 
                AFTER `plan_expires_at`
            """))
            db.commit()
            print("✅ plan_quota_reset_at 字段添加成功！")
        else:
            print("ℹ️  plan_quota_reset_at 字段已存在，跳过")
        
        # 检查并添加 is_unlimited 字段
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'users'
            AND COLUMN_NAME = 'is_unlimited'
        """))
        count = result.fetchone()[0]
        if count == 0:
            print("正在添加 is_unlimited 字段...")
            db.execute(text("""
                ALTER TABLE `users` 
                ADD COLUMN `is_unlimited` BOOLEAN NOT NULL DEFAULT FALSE 
                COMMENT '是否不限次数' 
                AFTER `plan_quota_reset_at`
            """))
            db.commit()
            print("✅ is_unlimited 字段添加成功！")
        else:
            print("ℹ️  is_unlimited 字段已存在，跳过")
        
        print("✅ 迁移完成：用户套餐订阅字段已添加")
            
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

