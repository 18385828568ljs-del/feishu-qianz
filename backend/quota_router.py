"""
配额和支付相关的 API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
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

@router.get("/pricing/plans", summary="获取套餐列表")
def get_pricing_plans(db: Session = Depends(get_db)):
    """获取所有上架的套餐列表（公开接口，不需要管理员权限）"""
    plans = quota_service.get_pricing_plans(db)
    return {"plans": plans}


@router.post("/payment/create", summary="创建支付订单")
def create_order(req: CreateOrderRequest, db: Session = Depends(get_db)):
    """创建支付订单"""
    result = quota_service.create_order(db, req.plan_id, req.open_id, req.tenant_key)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "CREATE_ORDER_FAILED"))
    return result


@router.get("/payment/status/{order_id}", summary="查询订单状态")
def get_order_status(order_id: str, db: Session = Depends(get_db)):
    """查询订单状态"""
    result = quota_service.get_order_status(db, order_id)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="订单不存在")
    return result



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


# ==================== 支付宝支付 API (YunGouOS) ====================

from fastapi import Request

class AlipayOrderRequest(BaseModel):
    """支付宝支付订单请求"""
    plan_id: str
    open_id: str
    tenant_key: str
    pay_type: str = "native"  # native 或 h5


@router.post("/payment/alipay/create", summary="创建支付宝支付订单")
def create_alipay_order(req: AlipayOrderRequest, db: Session = Depends(get_db)):
    """
    创建支付宝支付订单
    
    - pay_type: native（扫码支付）或 h5（H5支付）
    - 返回二维码URL或跳转URL
    """
    import logging
    logger = logging.getLogger("uvicorn.error")
    
    try:
        from payment.yungouos import yungouos_payment
        
        # 从数据库查找套餐
        from database import PricingPlan
        plan = db.query(PricingPlan).filter(
            PricingPlan.plan_id == req.plan_id,
            PricingPlan.is_active == True
        ).first()
        
        if not plan:
            logger.warning(f"Plan not found: {req.plan_id}")
            raise HTTPException(status_code=400, detail="套餐不存在")
        
        # 创建本地订单
        order_result = quota_service.create_order(db, req.plan_id, req.open_id, req.tenant_key)
        if not order_result.get("success"):
            logger.error(f"Failed to create local order: {order_result.get('error')}")
            raise HTTPException(status_code=400, detail=order_result.get("error", "创建订单失败"))
        
        order_id = order_result["order_id"]
        
        # 更新支付方式为支付宝
        from database import Order
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order:
            order.payment_method = "alipay"
            db.commit()
        
        amount = plan.price / 100.0  # 分转元
        body = f"数签助手-{plan.name}"
        
        # 附加数据：用于回调时识别用户
        attach = f"{req.open_id}|{req.tenant_key}|{req.plan_id}"
        
        # 调用 YunGouOS 创建支付
        if req.pay_type == "h5":
            result = yungouos_payment.h5_pay(order_id, amount, body, attach)
            if result["success"]:
                return {
                    "success": True,
                    "order_id": order_id,
                    "pay_type": "h5",
                    "pay_url": result["pay_url"],
                    "amount": plan.price,
                    "plan_name": plan.name,
                }
        else:
            result = yungouos_payment.native_pay(order_id, amount, body, attach)
            if result["success"]:
                return {
                    "success": True,
                    "order_id": order_id,
                    "pay_type": "native",
                    "qr_code": result["qr_code"],
                    "amount": plan.price,
                    "plan_name": plan.name,
                }
        
        # 支付创建失败
        error_msg = result.get("error", "支付创建失败")
        logger.error(f"YunGouOS payment creation failed: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error in create_alipay_order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")


@router.post("/payment/alipay/notify", summary="支付宝回调通知")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    """
    YunGouOS 支付回调通知
    
    收到通知后验签并更新订单状态
    """
    from payment.yungouos import yungouos_payment
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 获取表单数据
        form_data = await request.form()
        params = dict(form_data)
        logger.info(f"收到支付宝回调: {params}")
        
        # 处理回调
        result = yungouos_payment.handle_notify(params)
        
        if not result["success"]:
            logger.error(f"回调验证失败: {result.get('error')}")
            return "FAIL"
        
        out_trade_no = result["out_trade_no"]
        attach = result.get("attach", "")
        
        # 解析附加数据
        try:
            parts = attach.split("|")
            open_id = parts[0] if len(parts) > 0 else ""
            tenant_key = parts[1] if len(parts) > 1 else ""
            plan_id = parts[2] if len(parts) > 2 else ""
        except:
            open_id, tenant_key, plan_id = "", "", ""
        
        # 更新订单状态（使用模拟支付逻辑，实际会更新用户配额）
        pay_result = quota_service.mock_pay_order(db, out_trade_no)
        
        if pay_result.get("success"):
            logger.info(f"订单 {out_trade_no} 支付成功，配额已更新")
        else:
            logger.error(f"订单 {out_trade_no} 处理失败: {pay_result.get('error')}")
        
        # 返回 SUCCESS 告诉 YunGouOS 已收到通知
        return "SUCCESS"
        
    except Exception as e:
        logger.error(f"处理回调异常: {str(e)}")
        return "FAIL"


@router.get("/payment/alipay/query", summary="查询支付宝订单状态")
def query_alipay_order(order_id: str, db: Session = Depends(get_db)):
    """
    查询支付宝订单状态
    
    前端轮询此接口检查支付是否完成
    """
    # 先查本地订单状态
    local_result = quota_service.get_order_status(db, order_id)
    
    if not local_result.get("found"):
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 如果本地已经是 paid 状态，直接返回
    if local_result.get("status") == "paid":
        return {
            "success": True,
            "status": "paid",
            "order_id": order_id,
        }
    
    # 否则查询 YunGouOS
    from payment.yungouos import yungouos_payment
    result = yungouos_payment.query_order(order_id)
    
    if result["success"] and result.get("trade_state") == "SUCCESS":
        # 用户已支付，但回调可能还没到，手动处理
        pay_result = quota_service.mock_pay_order(db, order_id)
        return {
            "success": True,
            "status": "paid",
            "order_id": order_id,
        }
    
    return {
        "success": True,
        "status": local_result.get("status", "pending"),
        "order_id": order_id,
    }
