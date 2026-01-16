"""
数据库迁移脚本：为 pricing_plans 表添加月付/年付相关字段
执行方式：python -m migrations.add_pricing_plan_fields
或者在应用启动时自动执行
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text


def migrate():
    """执行迁移：添加月付/年付相关字段"""
    db = SessionLocal()
    try:
        # 检查 billing_type 字段是否已存在
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'pricing_plans'
            AND COLUMN_NAME = 'billing_type'
        """))
        
        count = result.fetchone()[0]
        
        if count == 0:
            print("正在添加新字段到 pricing_plans 表...")
            
            # 添加 billing_type 字段
            db.execute(text("""
                ALTER TABLE `pricing_plans` 
                ADD COLUMN `billing_type` VARCHAR(16) NOT NULL DEFAULT 'monthly' 
                COMMENT '计费类型：monthly 或 yearly' 
                AFTER `description`
            """))
            
            # 添加 monthly_price 字段
            db.execute(text("""
                ALTER TABLE `pricing_plans` 
                ADD COLUMN `monthly_price` INT NULL 
                COMMENT '月付价格（分），用于年付套餐显示节省' 
                AFTER `billing_type`
            """))
            
            # 添加 yearly_price 字段
            db.execute(text("""
                ALTER TABLE `pricing_plans` 
                ADD COLUMN `yearly_price` INT NULL 
                COMMENT '年付价格（分），用于月付套餐显示节省' 
                AFTER `monthly_price`
            """))
            
            # 添加 unlimited 字段
            db.execute(text("""
                ALTER TABLE `pricing_plans` 
                ADD COLUMN `unlimited` BOOLEAN NOT NULL DEFAULT FALSE 
                COMMENT '是否不限次数' 
                AFTER `yearly_price`
            """))
            
            # 添加 save_percent 字段
            db.execute(text("""
                ALTER TABLE `pricing_plans` 
                ADD COLUMN `save_percent` INT NULL 
                COMMENT '年付节省百分比（如24表示节省24%）' 
                AFTER `unlimited`
            """))
            
            # 修改 quota_count 字段允许 NULL（因为不限次数的套餐为 NULL）
            db.execute(text("""
                ALTER TABLE `pricing_plans` 
                MODIFY COLUMN `quota_count` INT NULL 
                COMMENT '签名次数（NULL表示不限次数）'
            """))
            
            db.commit()
            print("✅ pricing_plans 表字段添加成功！")
            
            # 删除旧的套餐数据，让系统重新初始化固定套餐
            print("正在清理旧套餐数据...")
            db.execute(text("DELETE FROM `pricing_plans`"))
            db.commit()
            print("✅ 旧套餐数据已清理，系统将在下次查询时自动初始化固定套餐")
        else:
            print("ℹ️  新字段已存在，跳过迁移")
            
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

