"""
手动给用户充值套餐的脚本
使用方法：python grant_plan.py <user_key> <plan_id>
"""
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

from database import User, PricingPlan

def grant_plan_to_user(user_identifier: str, plan_id: str):
    """
    给用户充值套餐
    user_identifier: user_key 或者 open_id
    plan_id: 套餐ID，如 pro_yearly
    """
    db = SessionLocal()
    
    try:
        # 查找用户
        user = db.query(User).filter(
            (User.user_key == user_identifier) | (User.open_id == user_identifier)
        ).first()
        
        if not user:
            print(f"❌ 用户不存在: {user_identifier}")
            print("\n💡 提示：请先在飞书中打开插件，让系统创建用户记录")
            return False
        
        print(f"✅ 找到用户: {user.user_key}")
        print(f"   当前配额: {user.remaining_quota}")
        print(f"   当前套餐: {user.current_plan_id or '无'}")
        
        # 查找套餐
        plan = db.query(PricingPlan).filter(PricingPlan.plan_id == plan_id).first()
        
        if not plan:
            print(f"❌ 套餐不存在: {plan_id}")
            print("\n可用套餐:")
            plans = db.query(PricingPlan).all()
            for p in plans:
                print(f"  - {p.plan_id}: {p.name} ({p.billing_type})")
            return False
        
        print(f"\n📦 套餐信息:")
        print(f"   名称: {plan.name}")
        print(f"   类型: {plan.billing_type}")
        print(f"   配额: {'不限次数' if plan.unlimited else f'{plan.quota_count}次'}")
        print(f"   价格: ¥{plan.price/100:.2f}")
        
        # 更新用户套餐
        now = datetime.utcnow()
        user.current_plan_id = plan.plan_id
        user.is_unlimited = plan.unlimited
        
        # 计算到期时间
        if plan.billing_type == "monthly":
            user.plan_expires_at = now + relativedelta(months=1)
            user.plan_quota_reset_at = now + relativedelta(months=1)
        elif plan.billing_type == "yearly":
            user.plan_expires_at = now + relativedelta(years=1)
            user.plan_quota_reset_at = now + relativedelta(years=1)
        
        # 设置配额
        if plan.unlimited:
            user.is_unlimited = True
        else:
            user.remaining_quota = plan.quota_count or 0
            user.is_unlimited = False
        
        db.commit()
        
        print(f"\n🎉 充值成功！")
        print(f"   新配额: {'不限次数' if user.is_unlimited else user.remaining_quota}")
        print(f"   到期时间: {user.plan_expires_at.strftime('%Y年%m月%d日 %H:%M:%S') if user.plan_expires_at else '无'}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ 充值失败: {str(e)}")
        return False
    finally:
        db.close()

def list_users(limit=10):
    """列出最近的用户"""
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
        print(f"\n最近 {limit} 个用户:")
        for u in users:
            print(f"  {u.user_key}")
            print(f"    配额: {u.remaining_quota}, 套餐: {u.current_plan_id or '无'}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 60)
        print("📦 用户套餐充值工具")
        print("=" * 60)
        print("\n使用方法:")
        print("  1. 列出用户: python grant_plan.py list")
        print("  2. 充值套餐: python grant_plan.py <user_key> <plan_id>")
        print("\n示例:")
        print("  python grant_plan.py list")
        print("  python grant_plan.py ou_xxx::xxx pro_yearly")
        print("\n可用套餐:")
        print("  - basic_monthly  : 入门版（月付）")
        print("  - basic_yearly   : 入门版（年付）")
        print("  - pro_monthly    : 专业版（月付）")
        print("  - pro_yearly     : 专业版（年付）")
        print("  - enterprise_monthly : 企业版（月付）")
        print("  - enterprise_yearly  : 企业版（年付）")
        sys.exit(1)
    
    if sys.argv[1] == "list":
        list_users()
    elif len(sys.argv) >= 3:
        user_key = sys.argv[1]
        plan_id = sys.argv[2]
        grant_plan_to_user(user_key, plan_id)
    else:
        print("❌ 参数错误")
        print("使用方法: python grant_plan.py <user_key> <plan_id>")
        print("或者: python grant_plan.py list")
