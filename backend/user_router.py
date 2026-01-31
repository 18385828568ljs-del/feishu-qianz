import time
import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Session

from database import Base, get_db
from auth_jwt import create_access_token

logger = logging.getLogger(__name__)


class AppUserIdentity(Base):
    __tablename__ = "app_user_identities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feishu_user_id = Column(String(128), nullable=False, index=True, unique=True)
    tenant_key = Column(String(128), nullable=True, index=True)
    fingerprint_hash = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('feishu_user_id', 'tenant_key', name='uq_user_tenant'),
    )


class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_type = Column(String(64), nullable=False, index=True)
    user_identity_id = Column(Integer, nullable=True, index=True)
    form_id = Column(String(32), nullable=True, index=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    origin = Column(Text, nullable=True)
    referer = Column(Text, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


router = APIRouter(prefix="/api/user", tags=["用户"])


class UserInitRequest(BaseModel):
    feishu_user_id: str = Field(..., min_length=1, max_length=128, description="飞书用户ID（必填）")
    tenant_key: str = Field(..., min_length=1, max_length=128, description="租户Key（必填）")
    fingerprint: str = Field(..., min_length=1, max_length=256, description="设备指纹（必填）")


class UserInitResponse(BaseModel):
    user_id: int
    feishu_user_id: str
    tenant_key: str
    token: str
    token_type: str = "bearer"
    expires_in: int = 60 * 60 * 24 * 7


# ===== 简易内存限流（单进程） =====
# key -> last_ts
_rate_limit_cache: dict[str, float] = {}


def _hash_fingerprint(fp: str) -> str:
    return hashlib.sha256(fp.encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def _rate_limit(key: str, min_interval_sec: float = 2.0) -> None:
    now = time.time()
    last = _rate_limit_cache.get(key)
    if last is not None and (now - last) < min_interval_sec:
        raise HTTPException(status_code=429, detail="TOO_MANY_REQUESTS")
    _rate_limit_cache[key] = now


def _log_activity(
    db: Session,
    activity_type: str,
    request: Request,
    user_identity_id: Optional[int] = None,
    form_id: Optional[str] = None,
    detail: Optional[str] = None,
):
    act = UserActivity(
        activity_type=activity_type,
        user_identity_id=user_identity_id,
        form_id=form_id,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        origin=request.headers.get("origin"),
        referer=request.headers.get("referer"),
        detail=detail,
    )
    db.add(act)


def _basic_source_check(request: Request) -> None:
    # 这是弱校验：仅用于降低滥用
    origin = (request.headers.get("origin") or "").lower()
    referer = (request.headers.get("referer") or "").lower()
    ua = (request.headers.get("user-agent") or "").lower()

    # allowlist 可通过环境变量扩展；这里先放宽，只做基本拦截
    if not ua:
        raise HTTPException(status_code=403, detail="MISSING_UA")

    # 允许的来源：飞书域名 + 本地开发环境
    allowed_origins = ["feishu", "larksuite", "localhost", "127.0.0.1"]
    
    # 如果带 origin/referer，检查是否来自允许的来源
    if origin and not any(allowed in origin for allowed in allowed_origins):
        raise HTTPException(status_code=403, detail="BAD_ORIGIN")
    if referer and not any(allowed in referer for allowed in allowed_origins):
        raise HTTPException(status_code=403, detail="BAD_REFERER")


@router.post("/init", response_model=UserInitResponse)
def init_user(req: UserInitRequest, request: Request, db: Session = Depends(get_db)):
    """初始化用户：信任飞书环境提供的 user_id，做弱校验+限流，创建用户并签发 7 天 JWT"""
    try:
        _basic_source_check(request)
        key = f"{_client_ip(request)}::{req.tenant_key or ''}::{req.feishu_user_id[:16]}"
        _rate_limit(key)

        fp_hash = _hash_fingerprint(req.fingerprint)

        user = db.query(AppUserIdentity).filter(AppUserIdentity.feishu_user_id == req.feishu_user_id).first()
        if not user:
            user = AppUserIdentity(
                feishu_user_id=req.feishu_user_id,
                tenant_key=req.tenant_key,
                fingerprint_hash=fp_hash,
            )
            db.add(user)
            db.flush()
            _log_activity(db, "user_init_create", request, user_identity_id=user.id)
        else:
            user.tenant_key = req.tenant_key
            user.fingerprint_hash = fp_hash
            user.last_seen_at = datetime.utcnow()
            _log_activity(db, "user_init_existing", request, user_identity_id=user.id)

        # 立即创建用户数据库和初始化配置
        user_key = f"{req.feishu_user_id}::{req.tenant_key}"
        from user_db_manager import ensure_user_database, get_user_session
        
        try:
            ensure_user_database(user_key)
            logger.info(f"User database ensured for {user_key}")
        except Exception as e:
            logger.error(f"Failed to ensure user database: {str(e)}", exc_info=True)
            raise
        
        # 初始化用户配置
        user_db = get_user_session(user_key)
        try:
            import quota_service
            logger.info(f"Initializing user profile for {user_key}")
            quota_service.get_or_create_user_profile(
                user_db, 
                req.feishu_user_id, 
                req.tenant_key
            )
            logger.info(f"User profile initialized successfully for {user_key}")
        except Exception as e:
            logger.error(f"Failed to initialize user profile: {str(e)}", exc_info=True)
            raise
        finally:
            user_db.close()

        token = create_access_token(user.id, user.feishu_user_id, user.tenant_key)
        logger.info(f"JWT token created for user {user.id}")

        db.commit()

        return UserInitResponse(
            user_id=user.id,
            feishu_user_id=user.feishu_user_id,
            tenant_key=user.tenant_key,
            token=token,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"User init failed: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"INIT_FAILED: {str(e)}")


def init_user_tables():
    from database import engine
    Base.metadata.create_all(bind=engine)

