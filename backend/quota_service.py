"""
配额管理服务
处理用户配额的查询、消耗、充值等逻辑

约定（混合模式）：
- 套餐/订单/邀请码/定价等仍使用共享库（Base）
- 用户剩余签字次数等配额状态，存放在每用户独立数据库的 user_profile（UserProfile）中
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy.orm import Session
from dateutil.relativedelta import relativedelta

from database import InviteCode, Order, SignatureLog, PricingPlan, UserProfile

# 新用户初始免费次数
FREE_TRIAL_QUOTA = 20

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
        "description": "每月2000次使用次数",
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
        "description": "每月6000次使用次数",
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
        "description": "年付¥899（相当于月付¥75，节省24%）",
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
        "description": "不限次数",
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
        "description": "年付¥2,388（相当于月付¥199，节省33%）",
    },
]


def get_user_key(open_id: str, tenant_key: str) -> str:
    """生成用户唯一标识"""
    return f"{open_id}::{tenant_key}"


# ==================== 用户库（独立库）配额逻辑 ====================

def get_or_create_user_profile(user_db: Session, open_id: str, tenant_key: str) -> UserProfile:
    """
    在用户独立库中获取或创建 user_profile
    
    注意：每个用户独立数据库应该只有一条记录，因为数据库本身就是按用户隔离的
    """
    # 先尝试根据 open_id 和 tenant_key 精确查询
    user = user_db.query(UserProfile).filter(
        UserProfile.open_id == open_id,
        UserProfile.tenant_key == tenant_key
    ).first()
    
    if not user:
        # 如果没找到，检查是否有其他记录（可能是旧数据）
        existing = user_db.query(UserProfile).first()
        if existing:
            # 发现不匹配的记录，这不应该发生
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Found mismatched profile in user DB: "
                f"expected {open_id}::{tenant_key}, "
                f"found {existing.open_id}::{existing.tenant_key}"
            )
            # 更新为正确的用户信息
            existing.open_id = open_id
            existing.tenant_key = tenant_key
            user_db.commit()
            user_db.refresh(existing)
            return existing
        
        # 创建新记录
        user = UserProfile(
            open_id=open_id,
            tenant_key=tenant_key,
            remaining_quota=FREE_TRIAL_QUOTA,
            total_used=0,
            total_paid=0,
            current_plan_id=None,
            plan_expires_at=None,
            plan_quota_reset_at=None,
            is_unlimited=False,
            invite_code_used=None,
            invite_expire_at=None,
        )
        user_db.add(user)
        user_db.commit()
        user_db.refresh(user)
    
    return user


def check_and_reset_quota(user_db: Session, user: UserProfile, shared_db: Session) -> None:
    """检查并重置用户配额（如果套餐到期或重置时间到了）。

    注意：套餐定义在共享库（PricingPlan）。
    """
    now = datetime.utcnow()

    if not user.current_plan_id:
        return

    # 套餐过期
    if user.plan_expires_at and user.plan_expires_at < now:
        user.current_plan_id = None
        user.plan_expires_at = None
        user.plan_quota_reset_at = None
        user.is_unlimited = False
        user_db.commit()
        return

    # 配额重置
    if user.plan_quota_reset_at and user.plan_quota_reset_at < now:
        plan = (
            shared_db.query(PricingPlan)
            .filter(PricingPlan.plan_id == user.current_plan_id)
            .first()
        )
        if plan:
            if plan.unlimited:
                user.is_unlimited = True
            else:
                user.remaining_quota = plan.quota_count or 0
                user.is_unlimited = False

            if plan.billing_type == "monthly":
                user.plan_quota_reset_at = user.plan_quota_reset_at + relativedelta(months=1)
            elif plan.billing_type == "yearly":
                user.plan_quota_reset_at = user.plan_quota_reset_at + relativedelta(years=1)

            user_db.commit()


def get_quota_status(user_db: Session, shared_db: Session, open_id: str, tenant_key: str) -> Dict[str, Any]:
    """获取用户配额状态（配额来自用户库，套餐信息来自共享库）。"""
    user = get_or_create_user_profile(user_db, open_id, tenant_key)

    check_and_reset_quota(user_db, user, shared_db)
    user_db.refresh(user)

    now = datetime.utcnow()
    invite_active = False
    invite_expire_at = None

    if user.invite_expire_at and user.invite_expire_at > now:
        invite_active = True
        invite_expire_at = int(user.invite_expire_at.timestamp())

    plan_quota = None
    if user.current_plan_id:
        plan = (
            shared_db.query(PricingPlan)
            .filter(PricingPlan.plan_id == user.current_plan_id)
            .first()
        )
        if plan and not plan.unlimited:
            plan_quota = plan.quota_count

    return {
        "remaining": user.remaining_quota if not user.is_unlimited else None,
        "plan_quota": plan_quota,
        "is_unlimited": user.is_unlimited,
        "total_used": user.total_used,
        "invite_active": invite_active,
        "invite_expire_at": invite_expire_at,
        "total_paid": user.total_paid,
        "current_plan_id": user.current_plan_id,
        "plan_expires_at": int(user.plan_expires_at.timestamp()) if user.plan_expires_at else None,
    }


def check_can_sign(user_db: Session, shared_db: Session, open_id: str, tenant_key: str) -> Dict[str, Any]:
    """检查用户是否可以签名（用户配额在用户库）。"""
    user = get_or_create_user_profile(user_db, open_id, tenant_key)

    check_and_reset_quota(user_db, user, shared_db)
    user_db.refresh(user)

    now = datetime.utcnow()

    if user.invite_expire_at and user.invite_expire_at > now:
        return {"can_sign": True, "reason": None, "consume_quota": False}

    if user.is_unlimited:
        return {"can_sign": True, "reason": None, "consume_quota": False}

    if user.remaining_quota > 0:
        return {"can_sign": True, "reason": None, "consume_quota": True}

    return {"can_sign": False, "reason": "NO_QUOTA", "consume_quota": False}


def consume_quota(
    user_db: Session,
    shared_db: Session,
    open_id: str,
    tenant_key: str,
    file_token: str = None,
    file_name: str = None,
    count: int = 1,
) -> bool:
    """消耗配额。
    
    - count: 消耗数量，默认为 1
    - 扣减发生在用户库 user_profile
    - 仍然把签名日志写到共享库 signature_logs（保持其它不变）
    """
    user = get_or_create_user_profile(user_db, open_id, tenant_key)

    check_and_reset_quota(user_db, user, shared_db)
    user_db.refresh(user)

    now = datetime.utcnow()
    quota_consumed = False

    if user.invite_expire_at and user.invite_expire_at > now:
        quota_consumed = False
    elif user.is_unlimited:
        quota_consumed = False
    elif user.remaining_quota >= count:
        user.remaining_quota -= count
        quota_consumed = True
    else:
        # 余额不足
        return False

    user.total_used += count
    user_db.commit()

    # 共享库日志仍保留
    user_key = get_user_key(open_id, tenant_key)
    log = SignatureLog(
        user_key=user_key,
        file_token=file_token,
        file_name=file_name,
        quota_consumed=quota_consumed,
    )
    shared_db.add(log)
    shared_db.commit()

    return True


def add_quota_to_user_profile(
    user_db: Session,
    open_id: str,
    tenant_key: str,
    quota_add: int | None,
    plan_id: str | None = None,
    plan_expires_at: datetime | None = None,
    plan_quota_reset_at: datetime | None = None,
    unlimited: bool | None = None,
    amount_paid: int | None = None,
) -> None:
    """购买成功后，把次数累加到用户独立库（B模式的关键）。"""
    user = get_or_create_user_profile(user_db, open_id, tenant_key)

    if plan_id is not None:
        user.current_plan_id = plan_id
    if plan_expires_at is not None:
        user.plan_expires_at = plan_expires_at
    if plan_quota_reset_at is not None:
        user.plan_quota_reset_at = plan_quota_reset_at
    if unlimited is not None:
        user.is_unlimited = unlimited

    if unlimited:
        # 不限次时不需要累加 remaining_quota
        pass
    else:
        if quota_add is not None and quota_add > 0:
            user.remaining_quota = (user.remaining_quota or 0) + int(quota_add)

    if amount_paid is not None and amount_paid > 0:
        user.total_paid = (user.total_paid or 0) + int(amount_paid)

    user_db.commit()


# ==================== 共享库（保持不变）的其它逻辑 ====================


def log_signature(shared_db: Session, open_id: str, tenant_key: str, file_token: str = None, file_name: str = None):
    """记录签名日志（共享库）。"""
    user_key = get_user_key(open_id, tenant_key)

    log = SignatureLog(
        user_key=user_key,
        file_token=file_token,
        file_name=file_name,
        quota_consumed=True,
    )

    shared_db.add(log)
    shared_db.commit()

    return True


def validate_invite_code(shared_db: Session, code: str) -> Dict[str, Any]:
    """验证邀请码是否有效（共享库）。"""
    invite = (
        shared_db.query(InviteCode)
        .filter(InviteCode.code == code, InviteCode.is_active == True)
        .first()
    )

    if not invite:
        return {"valid": False, "reason": "INVALID_CODE"}

    now = datetime.utcnow()

    if invite.expires_at and invite.expires_at < now:
        return {"valid": False, "reason": "CODE_EXPIRED"}

    if invite.used_count >= invite.max_usage:
        return {"valid": False, "reason": "CODE_USED_UP"}

    return {
        "valid": True,
        "benefit": f"{invite.benefit_days}天免费使用",
        "benefit_days": invite.benefit_days,
        "remaining_uses": invite.max_usage - invite.used_count,
    }


def redeem_invite_code(
    shared_db: Session, 
    user_db: Session,  # 新增: 必须传入用户库会话
    code: str, 
    open_id: str, 
    tenant_key: str
) -> Dict[str, Any]:
    """兑换邀请码（同时更新共享库和用户库）。"""
    validation = validate_invite_code(shared_db, code)
    if not validation["valid"]:
        return {"success": False, "error": validation["reason"]}

    # 1. 获取/创建用户配置（在用户库）
    user = get_or_create_user_profile(user_db, open_id, tenant_key)
    
    # 2. 检查是否正在生效
    if user.invite_code_used:
        # 如果当前有正在生效的邀请码，则不允许使用新码
        if user.invite_expire_at and user.invite_expire_at > datetime.utcnow():
            return {"success": False, "error": "ALREADY_USED_INVITE"}
        # 如果已过期，允许覆盖使用新码

    # 3. 获取邀请码信息（在共享库）
    invite = shared_db.query(InviteCode).filter(InviteCode.code == code).first()
    
    # 4. 更新用户状态（用户库）
    user.invite_code_used = code
    user.invite_expire_at = datetime.utcnow() + timedelta(days=invite.benefit_days)
    user_db.commit()

    # 5. 更新邀请码使用次数（共享库）
    invite.used_count += 1
    shared_db.commit()

    # 6. 同时更新旧的共享库 user 表（为了兼容性，防止旧逻辑查询失败）
    try:
        from database import User
        user_key = get_user_key(open_id, tenant_key)
        legacy_user = shared_db.query(User).filter(User.user_key == user_key).first()
        if legacy_user:
            legacy_user.invite_code_used = code
            legacy_user.invite_expire_at = user.invite_expire_at
            shared_db.commit()
    except Exception as e:
        print(f"Update legacy user failed: {e}")

    return {
        "success": True,
        "invite_expire_at": int(user.invite_expire_at.timestamp()),
        "benefit_days": invite.benefit_days,
    }


def create_invite_code(
    shared_db: Session,
    max_usage: int = 10,
    benefit_days: int = 365,
    expires_in_days: int = 30,
    created_by: str = None,
) -> Dict[str, Any]:
    """创建邀请码（共享库）。"""
    code = f"INV-{uuid.uuid4().hex[:8].upper()}"

    invite = InviteCode(
        code=code,
        max_usage=max_usage,
        benefit_days=benefit_days,
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
        created_by=created_by,
    )
    shared_db.add(invite)
    shared_db.commit()
    shared_db.refresh(invite)

    return {
        "code": code,
        "max_usage": max_usage,
        "benefit_days": benefit_days,
        "expires_at": int(invite.expires_at.timestamp()) if invite.expires_at else None,
    }


def init_default_pricing_plans(shared_db: Session) -> None:
    """初始化默认套餐（共享库）。"""
    existing_count = shared_db.query(PricingPlan).count()
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
            shared_db.add(plan)
        shared_db.commit()


def get_pricing_plans(shared_db: Session) -> list:
    """获取定价方案列表（共享库）。"""
    init_default_pricing_plans(shared_db)

    plans = (
        shared_db.query(PricingPlan)
        .filter(PricingPlan.is_active == True)
        .order_by(PricingPlan.sort_order)
        .all()
    )

    return [
        {
            "id": p.plan_id,
            "name": p.name,
            "count": p.quota_count,
            "price": p.price,
            "description": p.description,
            "billing_type": p.billing_type,
            "monthly_price": p.monthly_price,
            "yearly_price": p.yearly_price,
            "unlimited": p.unlimited,
            "save_percent": p.save_percent,
        }
        for p in plans
    ]


def create_order(shared_db: Session, plan_id: str, open_id: str, tenant_key: str) -> Dict[str, Any]:
    """创建支付订单（共享库，保持不变）。"""
    plan_obj = (
        shared_db.query(PricingPlan)
        .filter(PricingPlan.plan_id == plan_id, PricingPlan.is_active == True)
        .first()
    )
    if not plan_obj:
        return {"success": False, "error": "INVALID_PLAN"}

    user_key = get_user_key(open_id, tenant_key)

    order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    order = Order(
        order_id=order_id,
        user_key=user_key,
        plan_id=plan_id,
        quota_count=plan_obj.quota_count,
        amount=plan_obj.price,
        payment_method="mock",
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    shared_db.add(order)
    shared_db.commit()
    shared_db.refresh(order)

    return {
        "success": True,
        "order_id": order_id,
        "amount": plan_obj.price,
        "quota_count": plan_obj.quota_count,
        "plan_name": plan_obj.name,
        "expires_at": int(order.expires_at.timestamp()),
    }


def mock_pay_order(shared_db: Session, order_id: str) -> Dict[str, Any]:
    """模拟支付订单（共享库订单状态更新；用户库次数累加）。"""
    order = shared_db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        return {"success": False, "error": "ORDER_NOT_FOUND"}

    if order.status != "pending":
        return {"success": False, "error": f"ORDER_STATUS_INVALID: {order.status}"}

    now = datetime.utcnow()
    if order.expires_at and order.expires_at < now:
        order.status = "expired"
        shared_db.commit()
        return {"success": False, "error": "ORDER_EXPIRED"}

    plan = shared_db.query(PricingPlan).filter(PricingPlan.plan_id == order.plan_id).first()
    if not plan:
        return {"success": False, "error": "PLAN_NOT_FOUND"}

    # 订单支付成功
    order.status = "paid"
    order.paid_at = now

    # 解析 user_key
    try:
        open_id, tenant_key = order.user_key.split("::", 1)
    except Exception:
        open_id, tenant_key = "", ""

    # 同步到用户独立库：累加次数
    from user_db_manager import ensure_user_database, get_user_session

    ensure_user_database(order.user_key)
    user_db = get_user_session(order.user_key)
    try:
        if plan.billing_type == "monthly":
            plan_expires_at = now + relativedelta(months=1)
            plan_quota_reset_at = now + relativedelta(months=1)
        elif plan.billing_type == "yearly":
            plan_expires_at = now + relativedelta(years=1)
            plan_quota_reset_at = now + relativedelta(years=1)
        else:
            plan_expires_at = now + relativedelta(months=1)
            plan_quota_reset_at = now + relativedelta(months=1)

        add_quota_to_user_profile(
            user_db=user_db,
            open_id=open_id,
            tenant_key=tenant_key,
            quota_add=plan.quota_count,
            plan_id=order.plan_id,
            plan_expires_at=plan_expires_at,
            plan_quota_reset_at=plan_quota_reset_at,
            unlimited=bool(plan.unlimited),
            amount_paid=order.amount,
        )
    finally:
        user_db.close()

    shared_db.commit()

    return {
        "success": True,
        "order_id": order_id,
        "quota_added": plan.quota_count,
        "is_unlimited": plan.unlimited,
        "new_remaining": None,
        "plan_expires_at": int((now + relativedelta(months=1)).timestamp()) if plan.billing_type == "monthly" else int((now + relativedelta(years=1)).timestamp()),
    }


def get_order_status(shared_db: Session, order_id: str) -> Dict[str, Any]:
    """查询订单状态（共享库）。"""
    order = shared_db.query(Order).filter(Order.order_id == order_id).first()

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
