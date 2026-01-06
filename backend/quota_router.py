"""
配额和支付相关的 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, init_db
import quota_service

router = APIRouter(prefix="/api", tags=["quota"])


# ==================== 请求/响应模型 ====================

class QuotaStatusResponse(BaseModel):
    remaining: int
    total_used: int
    invite_active: bool
    invite_expire_at: Optional[int] = None
    total_paid: int


class CanSignResponse(BaseModel):
    can_sign: bool
    reason: Optional[str] = None
    consume_quota: bool


class InviteValidateRequest(BaseModel):
    code: str


class InviteRedeemRequest(BaseModel):
    code: str
    open_id: str
    tenant_key: str


class CreateOrderRequest(BaseModel):
    plan_id: str
    open_id: str
    tenant_key: str


class MockPayRequest(BaseModel):
    order_id: str


class CreateInviteRequest(BaseModel):
    max_usage: int = 10
    benefit_days: int = 365
    expires_in_days: int = 30


# ==================== 配额 API ====================

@router.get("/quota/status")
def get_quota_status(open_id: str, tenant_key: str, db: Session = Depends(get_db)):
    """
    获取用户配额状态
    
    优先使用飞书官方API，降级使用本地管理
    """
    # 导入飞书官方支付服务
    from payment.feishu_official import feishu_payment_service
    
    try:
        # 调用飞书官方API获取权益
        result = feishu_payment_service.check_user_paid_scope(open_id, tenant_key)
        
        # 检查是否需要降级到本地管理
        if result.get('use_local', False):
            # 使用本地配额管理
            return quota_service.get_quota_status(db, open_id, tenant_key)
        
        # 兼容原有格式返回
        return QuotaStatusResponse(
            remaining=result['remaining_quota'],
            total_used=0,  # 飞书API可能不返回总使用量
            invite_active=False,  # 使用飞书官方支付后,邀请码功能可禁用
            invite_expire_at=None,
            total_paid=0  # 飞书API可能不返回总付费金额
        )
    except Exception as e:
        print(f"获取配额状态失败: {str(e)}")
        # 降级到本地管理
        return quota_service.get_quota_status(db, open_id, tenant_key)


@router.get("/quota/check")
def check_can_sign(open_id: str, tenant_key: str, db: Session = Depends(get_db)):
    """
    检查用户是否可以签名
    
    改用飞书官方付费能力API进行权益校验
    """
    # 导入飞书官方支付服务
    from payment.feishu_official import feishu_payment_service
    
    try:
        # 调用飞书官方API检查权益
        result = feishu_payment_service.check_user_paid_scope(open_id, tenant_key)
        
        if result['is_need_pay']:
            # 用户需要购买
            marketplace_url = feishu_payment_service.get_marketplace_url()
            return CanSignResponse(
                can_sign=False,
                reason=f"请前往插件市场购买: {marketplace_url}",
                consume_quota=False
            )
        
        if not result['has_permission']:
            # 配额已用完
            return CanSignResponse(
                can_sign=False,
                reason="配额已用完,请购买套餐",
                consume_quota=False
            )
        
        # 有权限可以签名
        return CanSignResponse(
            can_sign=True,
            reason=None,
            consume_quota=True
        )
        
    except Exception as e:
        # API调用失败,返回错误
        print(f"飞书API调用失败: {str(e)}")
        return CanSignResponse(
            can_sign=False,
            reason="系统错误,请稍后重试",
            consume_quota=False
        )


@router.post("/quota/consume")
def consume_quota(open_id: str, tenant_key: str, file_token: str = None, 
                  file_name: str = None, db: Session = Depends(get_db)):
    """
    消耗一次配额(签名成功后调用)
    
    改用飞书官方API进行配额扣减
    """
    # 导入飞书官方支付服务
    from payment.feishu_official import feishu_payment_service
    
    try:
        # 先检查权益
        check_result = feishu_payment_service.check_user_paid_scope(open_id, tenant_key)
        
        if not check_result['has_permission']:
            raise HTTPException(status_code=402, detail="NO_QUOTA")
        
        # 调用飞书API扣减配额
        success = feishu_payment_service.consume_quota(open_id, tenant_key, count=1)
        
        if not success:
            raise HTTPException(status_code=500, detail="扣减配额失败")
        
        # 记录签名日志到本地数据库(可选)
        quota_service.log_signature(db, open_id, tenant_key, file_token, file_name)
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"消耗配额失败: {str(e)}")
        raise HTTPException(status_code=500, detail="系统错误")



# ==================== 邀请码 API ====================

@router.post("/invite/validate")
def validate_invite(req: InviteValidateRequest, db: Session = Depends(get_db)):
    """验证邀请码是否有效（不消耗次数）"""
    return quota_service.validate_invite_code(db, req.code)


@router.post("/invite/redeem")
def redeem_invite(req: InviteRedeemRequest, db: Session = Depends(get_db)):
    """兑换邀请码"""
    result = quota_service.redeem_invite_code(db, req.code, req.open_id, req.tenant_key)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "REDEEM_FAILED"))
    return result


# ==================== 支付 API ====================
# 注意：支付功能已迁移到飞书官方付费能力
# 用户通过飞书插件详情页购买，无需后端支付接口



# ==================== 管理 API ====================

# 注意：这些接口需要管理员权限
# 从 admin_router 导入权限验证
from admin_router import verify_admin
from fastapi import Header

@router.post("/admin/invite/create")
def create_invite(
    req: CreateInviteRequest, 
    db: Session = Depends(get_db),
    x_admin_token: str = Header(None)
):
    """创建邀请码（管理接口），需要管理员权限"""
    # 验证管理员权限
    from admin_router import get_admin_password
    if x_admin_token != get_admin_password():
        raise HTTPException(status_code=401, detail="未授权访问")
    
    return quota_service.create_invite_code(
        db, 
        max_usage=req.max_usage,
        benefit_days=req.benefit_days,
        expires_in_days=req.expires_in_days
    )


@router.post("/admin/db/init")
def init_database(x_admin_token: str = Header(None)):
    """初始化数据库（创建表），需要管理员权限"""
    # 验证管理员权限
    from admin_router import get_admin_password
    if x_admin_token != get_admin_password():
        raise HTTPException(status_code=401, detail="未授权访问")
    
    try:
        init_db()
        return {"success": True, "message": "Database initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

