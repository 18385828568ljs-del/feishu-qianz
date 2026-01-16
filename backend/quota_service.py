"""
配额管理服务
处理用户配额的查询、消耗、充值等逻辑
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from dateutil.relativedelta import relativedelta

from database import User, InviteCode, Order, SignatureLog, PricingPlan

# 免费试用次数
FREE_TRIAL_QUOTA = 10

# 默认定价方案（数据库为空时自动初始化）
# 固定套餐方案，不需要后台配置
DEFAULT_PRICING_PLANS = [
    {
        "id": "basic_monthly",
        "name": "入门版",
        "count": 2000,
        "price": 2900,  # 29元
        "billing_type": "monthly",
        "unlimited": False,
        "sort_order": 1,
        "description": "每月2000次使用次数"
    },
    {
        "id": "pro_monthly",
        "name": "专业版",
        "count": 6000,
        "price": 9900,  # 99元
        "billing_type": "monthly",
        "monthly_price": 9900,
        "yearly_price": 89900,  # 年付价格，用于显示节省
        "save_percent": 24,
        "unlimited": False,
        "sort_order": 2,
        "description": "每月6000次使用次数"
    },
    {
        "id": "pro_yearly",
        "name": "专业版",
        "count": 6000,
        "price": 89900,  # 899元
        "billing_type": "yearly",
        "monthly_price": 9900,  # 月付价格，用于显示节省
        "yearly_price": 89900,
        "save_percent": 24,
        "unlimited": False,
        "sort_order": 3,
        "description": "年付¥899（相当于月付¥75，节省24%）"
    },
    {
        "id": "enterprise_monthly",
        "name": "企业版",
        "count": None,  # 不限次数
        "price": 29900,  # 299元
        "billing_type": "monthly",
        "monthly_price": 29900,
        "yearly_price": 238800,  # 年付价格，用于显示节省
        "save_percent": 33,
        "unlimited": True,
        "sort_order": 4,
        "description": "不限次数"
    },
    {
        "id": "enterprise_yearly",
        "name": "企业版",
        "count": None,  # 不限次数
        "price": 238800,  # 2388元
        "billing_type": "yearly",
        "monthly_price": 29900,  # 月付价格，用于显示节省
        "yearly_price": 238800,
        "save_percent": 33,
        "unlimited": True,
        "sort_order": 5,
        "description": "年付¥2,388（相当于月付¥199，节省33%）"
    },
]


def get_user_key(open_id: str, tenant_key: str) -> str:
    """生成用户唯一标识"""
    return f"{open_id}::{tenant_key}"


def get_or_create_user(db: Session, open_id: str, tenant_key: str) -> User:
    """获取或创建用户"""
    user_key = get_user_key(open_id, tenant_key)
    user = db.query(User).filter(User.user_key == user_key).first()
    
    if not user:
        user = User(
            open_id=open_id,
            tenant_key=tenant_key,
            user_key=user_key,
            remaining_quota=FREE_TRIAL_QUOTA,
            total_used=0,
            total_paid=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user


def check_and_reset_quota(db: Session, user: User) -> None:
    """检查并重置用户配额（如果套餐到期或重置时间到了）"""
    now = datetime.utcnow()
    
    # 如果用户没有套餐，不需要重置
    if not user.current_plan_id:
        return
    
    # 检查套餐是否过期
    if user.plan_expires_at and user.plan_expires_at < now:
        # 套餐已过期，清除套餐信息
        user.current_plan_id = None
        user.plan_expires_at = None
        user.plan_quota_reset_at = None
        user.is_unlimited = False
        # 保留剩余配额（不清零），但不再自动重置
        db.commit()
        return
    
    # 检查是否需要重置配额（月付每月重置，年付每年重置）
    if user.plan_quota_reset_at and user.plan_quota_reset_at < now:
        # 获取套餐信息
        plan = db.query(PricingPlan).filter(PricingPlan.plan_id == user.current_plan_id).first()
        if plan:
            if plan.unlimited:
                # 不限次数，不需要重置配额
                user.is_unlimited = True
            else:
                # 重置配额到套餐的配额数
                user.remaining_quota = plan.quota_count or 0
                user.is_unlimited = False
            
            # 计算下次重置时间
            if plan.billing_type == "monthly":
                # 月付：每月重置
                user.plan_quota_reset_at = user.plan_quota_reset_at + relativedelta(months=1)
            elif plan.billing_type == "yearly":
                # 年付：每年重置
                user.plan_quota_reset_at = user.plan_quota_reset_at + relativedelta(years=1)
            
            db.commit()


def get_quota_status(db: Session, open_id: str, tenant_key: str) -> Dict[str, Any]:
    """获取用户配额状态"""
    user = get_or_create_user(db, open_id, tenant_key)
    
    # 检查并重置配额（如果需要）
    check_and_reset_quota(db, user)
    db.refresh(user)
    
    now = datetime.utcnow()
    invite_active = False
    invite_expire_at = None
    
    if user.invite_expire_at and user.invite_expire_at > now:
        invite_active = True
        invite_expire_at = int(user.invite_expire_at.timestamp())
    
    # 获取套餐总配额
    plan_quota = None
    if user.current_plan_id:
        plan = db.query(PricingPlan).filter(PricingPlan.plan_id == user.current_plan_id).first()
        if plan and not plan.unlimited:
            plan_quota = plan.quota_count
    elif not user.invite_expire_at or user.invite_expire_at <= now:
        # 免费试用用户，总配额为 FREE_TRIAL_QUOTA
        plan_quota = FREE_TRIAL_QUOTA
    
    return {
        "remaining": user.remaining_quota if not user.is_unlimited else None,
        "plan_quota": plan_quota,  # 套餐总配额（用于进度条显示）
        "is_unlimited": user.is_unlimited,
        "total_used": user.total_used,
        "invite_active": invite_active,
        "invite_expire_at": invite_expire_at,
        "total_paid": user.total_paid,
        "current_plan_id": user.current_plan_id,
        "plan_expires_at": int(user.plan_expires_at.timestamp()) if user.plan_expires_at else None,
    }


def check_can_sign(db: Session, open_id: str, tenant_key: str) -> Dict[str, Any]:
    """检查用户是否可以签名"""
    user = get_or_create_user(db, open_id, tenant_key)
    
    # 检查并重置配额（如果需要）
    check_and_reset_quota(db, user)
    db.refresh(user)
    
    now = datetime.utcnow()
    
    # 检查邀请码是否有效
    if user.invite_expire_at and user.invite_expire_at > now:
        return {"can_sign": True, "reason": None, "consume_quota": False}
    
    # 检查是否不限次数
    if user.is_unlimited:
        return {"can_sign": True, "reason": None, "consume_quota": False}
    
    # 检查剩余配额
    if user.remaining_quota > 0:
        return {"can_sign": True, "reason": None, "consume_quota": True}
    
    return {"can_sign": False, "reason": "NO_QUOTA", "consume_quota": False}


def consume_quota(db: Session, open_id: str, tenant_key: str, file_token: str = None, file_name: str = None) -> bool:
    """消耗一次配额"""
    user = get_or_create_user(db, open_id, tenant_key)
    
    # 检查并重置配额（如果需要）
    check_and_reset_quota(db, user)
    db.refresh(user)
    
    now = datetime.utcnow()
    quota_consumed = False
    
    # 如果邀请码有效，不消耗配额
    if user.invite_expire_at and user.invite_expire_at > now:
        quota_consumed = False
    elif user.is_unlimited:
        # 不限次数，不消耗配额
        quota_consumed = False
    elif user.remaining_quota > 0:
        user.remaining_quota -= 1
        quota_consumed = True
    else:
        return False  # 没有配额，无法消耗
    
    # 增加使用次数
    user.total_used += 1
    
    # 记录签名日志
    log = SignatureLog(
        user_key=user.user_key,
        file_token=file_token,
        file_name=file_name,
        quota_consumed=quota_consumed,
    )
    db.add(log)
    db.commit()
    
    return True


def log_signature(db: Session, open_id: str, tenant_key: str, file_token: str = None, file_name: str = None):
    """
    记录签名日志
    
    使用飞书官方支付后,本地只记录日志,不管理配额
    """
    user_key = get_user_key(open_id, tenant_key)
    
    # 创建签名日志记录
    log = SignatureLog(
        user_key=user_key,
        file_token=file_token,
        file_name=file_name,
        quota_consumed=True  # 标记已消耗配额
    )
    
    db.add(log)
    db.commit()
    
    return True


def validate_invite_code(db: Session, code: str) -> Dict[str, Any]:
    """验证邀请码是否有效（不消耗次数）"""
    invite = db.query(InviteCode).filter(
        InviteCode.code == code,
        InviteCode.is_active == True
    ).first()
    
    if not invite:
        return {"valid": False, "reason": "INVALID_CODE"}
    
    now = datetime.utcnow()
    
    # 检查是否过期
    if invite.expires_at and invite.expires_at < now:
        return {"valid": False, "reason": "CODE_EXPIRED"}
    
    # 检查使用次数
    if invite.used_count >= invite.max_usage:
        return {"valid": False, "reason": "CODE_USED_UP"}
    
    return {
        "valid": True,
        "benefit": f"{invite.benefit_days}天免费使用",
        "benefit_days": invite.benefit_days,
        "remaining_uses": invite.max_usage - invite.used_count,
    }


def redeem_invite_code(db: Session, code: str, open_id: str, tenant_key: str) -> Dict[str, Any]:
    """兑换邀请码"""
    # 先验证
    validation = validate_invite_code(db, code)
    if not validation["valid"]:
        return {"success": False, "error": validation["reason"]}
    
    user = get_or_create_user(db, open_id, tenant_key)
    
    # 检查用户是否已使用过邀请码
    if user.invite_code_used:
        return {"success": False, "error": "ALREADY_USED_INVITE"}
    
    # 获取邀请码
    invite = db.query(InviteCode).filter(InviteCode.code == code).first()
    
    # 更新用户
    user.invite_code_used = code
    user.invite_expire_at = datetime.utcnow() + timedelta(days=invite.benefit_days)
    
    # 增加邀请码使用计数
    invite.used_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "invite_expire_at": int(user.invite_expire_at.timestamp()),
        "benefit_days": invite.benefit_days,
    }


def create_invite_code(db: Session, max_usage: int = 10, benefit_days: int = 365, 
                       expires_in_days: int = 30, created_by: str = None) -> Dict[str, Any]:
    """创建邀请码（管理接口）"""
    # 生成唯一码
    code = f"INV-{uuid.uuid4().hex[:8].upper()}"
    
    invite = InviteCode(
        code=code,
        max_usage=max_usage,
        benefit_days=benefit_days,
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
        created_by=created_by,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    
    return {
        "code": code,
        "max_usage": max_usage,
        "benefit_days": benefit_days,
        "expires_at": int(invite.expires_at.timestamp()) if invite.expires_at else None,
    }


def init_default_pricing_plans(db: Session) -> None:
    """初始化默认套餐（如果数据库为空）"""
    existing_count = db.query(PricingPlan).count()
    if existing_count == 0:
        for plan_data in DEFAULT_PRICING_PLANS:
            plan = PricingPlan(
                plan_id=plan_data["id"],
                name=plan_data["name"],
                quota_count=plan_data.get("count"),
                price=plan_data["price"],
                sort_order=plan_data.get("sort_order", 0),
                is_active=True,
                billing_type=plan_data.get("billing_type", "monthly"),
                monthly_price=plan_data.get("monthly_price"),
                yearly_price=plan_data.get("yearly_price"),
                unlimited=plan_data.get("unlimited", False),
                save_percent=plan_data.get("save_percent"),
                description=plan_data.get("description"),
            )
            db.add(plan)
        db.commit()


def get_pricing_plans(db: Session) -> list:
    """获取定价方案列表（从数据库）"""
    # 如果数据库为空，自动初始化默认套餐
    init_default_pricing_plans(db)
    
    plans = db.query(PricingPlan).filter(
        PricingPlan.is_active == True
    ).order_by(PricingPlan.sort_order).all()
    
    return [
        {
            "id": p.plan_id,
            "name": p.name,
            "count": p.quota_count,  # None表示不限次数
            "price": p.price,
            "description": p.description,
            "billing_type": p.billing_type,  # monthly 或 yearly
            "monthly_price": p.monthly_price,
            "yearly_price": p.yearly_price,
            "unlimited": p.unlimited,
            "save_percent": p.save_percent,
        }
        for p in plans
    ]


def create_order(db: Session, plan_id: str, open_id: str, tenant_key: str) -> Dict[str, Any]:
    """创建支付订单"""
    # 从数据库查找套餐
    plan_obj = db.query(PricingPlan).filter(
        PricingPlan.plan_id == plan_id,
        PricingPlan.is_active == True
    ).first()
    if not plan_obj:
        return {"success": False, "error": "INVALID_PLAN"}
    
    user = get_or_create_user(db, open_id, tenant_key)
    
    # 生成订单号
    order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    
    order = Order(
        order_id=order_id,
        user_key=user.user_key,
        plan_id=plan_id,
        quota_count=plan_obj.quota_count,
        amount=plan_obj.price,
        payment_method="mock",
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=30),  # 30分钟过期
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return {
        "success": True,
        "order_id": order_id,
        "amount": plan_obj.price,
        "quota_count": plan_obj.quota_count,
        "plan_name": plan_obj.name,
        "expires_at": int(order.expires_at.timestamp()),
    }


def mock_pay_order(db: Session, order_id: str) -> Dict[str, Any]:
    """模拟支付订单（测试用）"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        return {"success": False, "error": "ORDER_NOT_FOUND"}
    
    if order.status != "pending":
        return {"success": False, "error": f"ORDER_STATUS_INVALID: {order.status}"}
    
    now = datetime.utcnow()
    if order.expires_at and order.expires_at < now:
        order.status = "expired"
        db.commit()
        return {"success": False, "error": "ORDER_EXPIRED"}
    
    # 获取套餐信息
    plan = db.query(PricingPlan).filter(PricingPlan.plan_id == order.plan_id).first()
    if not plan:
        return {"success": False, "error": "PLAN_NOT_FOUND"}
    
    # 更新订单状态
    order.status = "paid"
    order.paid_at = now
    
    # 更新用户套餐和配额
    user = db.query(User).filter(User.user_key == order.user_key).first()
    if user:
        # 设置用户当前套餐
        user.current_plan_id = order.plan_id
        user.is_unlimited = plan.unlimited
        
        # 计算套餐到期时间
        if plan.billing_type == "monthly":
            user.plan_expires_at = now + relativedelta(months=1)
            user.plan_quota_reset_at = now + relativedelta(months=1)
        elif plan.billing_type == "yearly":
            user.plan_expires_at = now + relativedelta(years=1)
            user.plan_quota_reset_at = now + relativedelta(years=1)
        else:
            # 默认月付
            user.plan_expires_at = now + relativedelta(months=1)
            user.plan_quota_reset_at = now + relativedelta(months=1)
        
        # 设置配额
        if plan.unlimited:
            # 不限次数，不设置配额
            user.is_unlimited = True
            quota_added = None
        else:
            # 设置配额为套餐的配额数（不是累加）
            user.remaining_quota = plan.quota_count or 0
            user.is_unlimited = False
            quota_added = plan.quota_count
        
        user.total_paid += order.amount
    
    db.commit()
    
    return {
        "success": True,
        "order_id": order_id,
        "quota_added": quota_added,
        "is_unlimited": plan.unlimited,
        "new_remaining": None if plan.unlimited else (user.remaining_quota if user else 0),
        "plan_expires_at": int(user.plan_expires_at.timestamp()) if user and user.plan_expires_at else None,
    }


def get_order_status(db: Session, order_id: str) -> Dict[str, Any]:
    """查询订单状态"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    
    if not order:
        return {"found": False}
    
    return {
        "found": True,
        "order_id": order.order_id,
        "status": order.status,
        "amount": order.amount,
        "quota_count": order.quota_count,
        "created_at": int(order.created_at.timestamp()),
        "paid_at": int(order.paid_at.timestamp()) if order.paid_at else None,
    }
