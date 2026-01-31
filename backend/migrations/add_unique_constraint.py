"""
数据库迁移脚本：添加用户唯一性约束
执行时间：2026-01-30
目的：确保 (feishu_user_id, tenant_key) 组合唯一
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 添加父目录到路径，以便导入配置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# 数据库配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "feishu")

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"


def check_duplicate_records(engine):
    """检查是否存在重复记录"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT feishu_user_id, tenant_key, COUNT(*) as count
            FROM app_user_identities
            GROUP BY feishu_user_id, tenant_key
            HAVING count > 1
        """))
        duplicates = result.fetchall()
        return duplicates


def clean_duplicate_records(engine):
    """清理重复记录，保留最早创建的记录"""
    with engine.connect() as conn:
        # 查找重复记录
        duplicates = check_duplicate_records(engine)
        
        if not duplicates:
            print("✅ 没有发现重复记录")
            return True
        
        print(f"⚠️  发现 {len(duplicates)} 组重复记录")
        
        for feishu_user_id, tenant_key, count in duplicates:
            print(f"   - {feishu_user_id} / {tenant_key}: {count} 条记录")
            
            # 保留最早创建的记录，删除其他
            conn.execute(text("""
                DELETE FROM app_user_identities
                WHERE (feishu_user_id, tenant_key) = (:user_id, :tenant)
                AND id NOT IN (
                    SELECT * FROM (
                        SELECT MIN(id) 
                        FROM app_user_identities 
                        WHERE feishu_user_id = :user_id AND tenant_key = :tenant
                    ) as tmp
                )
            """), {"user_id": feishu_user_id, "tenant": tenant_key})
        
        conn.commit()
        print("✅ 重复记录已清理")
        return True


def add_unique_constraint(engine):
    """添加唯一性约束"""
    with engine.connect() as conn:
        # 检查约束是否已存在
        result = conn.execute(text("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.TABLE_CONSTRAINTS 
            WHERE TABLE_SCHEMA = :db_name 
            AND TABLE_NAME = 'app_user_identities' 
            AND CONSTRAINT_NAME = 'uq_user_tenant'
        """), {"db_name": MYSQL_DATABASE})
        
        if result.fetchone():
            print("✅ 唯一性约束已存在，无需重复添加")
            return True
        
        # 添加唯一性约束
        try:
            conn.execute(text("""
                ALTER TABLE app_user_identities 
                ADD CONSTRAINT uq_user_tenant 
                UNIQUE (feishu_user_id, tenant_key)
            """))
            conn.commit()
            print("✅ 唯一性约束添加成功")
            return True
        except Exception as e:
            print(f"❌ 添加约束失败: {e}")
            return False


def main():
    """主函数"""
    print("=" * 60)
    print("数据库迁移：添加用户唯一性约束")
    print("=" * 60)
    print()
    
    try:
        # 创建数据库引擎
        engine = create_engine(DATABASE_URL, echo=False)
        print(f"📊 连接数据库: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")
        print()
        
        # 步骤 1: 检查并清理重复记录
        print("步骤 1: 检查重复记录...")
        if not clean_duplicate_records(engine):
            print("❌ 清理重复记录失败")
            return False
        print()
        
        # 步骤 2: 添加唯一性约束
        print("步骤 2: 添加唯一性约束...")
        if not add_unique_constraint(engine):
            print("❌ 添加约束失败")
            return False
        print()
        
        print("=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
