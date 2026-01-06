"""
MySQL 数据库配置和模型定义
使用 SQLAlchemy ORM
"""
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import sessionmaker, declarative_base

# 加载 .env 文件
load_dotenv()

# 从环境变量读取数据库配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "feishu")

# 构建数据库URL
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# 创建引擎
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    open_id = Column(String(128), nullable=False, index=True)
    tenant_key = Column(String(128), nullable=False, index=True)
    user_key = Column(String(256), unique=True, nullable=False, index=True)  # open_id::tenant_key
    
    # 配额相关
    remaining_quota = Column(Integer, default=20, nullable=False)  # 剩余次数
    total_used = Column(Integer, default=0, nullable=False)  # 总使用次数
    
    # 邀请码相关
    invite_code_used = Column(String(64), nullable=True)  # 使用的邀请码
    invite_expire_at = Column(DateTime, nullable=True)  # 邀请有效期
    
    # 付费相关
    total_paid = Column(Integer, default=0, nullable=False)  # 累计付费金额（分）
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class InviteCode(Base):
    """邀请码表"""
    __tablename__ = "invite_codes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    
    # 使用限制
    max_usage = Column(Integer, default=10, nullable=False)  # 最大使用次数
    used_count = Column(Integer, default=0, nullable=False)  # 已使用次数
    
    # 有效期
    expires_at = Column(DateTime, nullable=True)  # 邀请码过期时间
    benefit_days = Column(Integer, default=365, nullable=False)  # 受益天数（默认1年）
    
    # 创建者
    created_by = Column(String(128), nullable=True)
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Order(Base):
    """订单表"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), unique=True, nullable=False, index=True)
    user_key = Column(String(256), nullable=False, index=True)
    
    # 订单内容
    plan_id = Column(String(32), nullable=False)  # 套餐ID
    quota_count = Column(Integer, nullable=False)  # 购买次数
    amount = Column(Integer, nullable=False)  # 金额（分）
    
    # 支付信息
    payment_method = Column(String(32), default="mock", nullable=False)  # mock, wechat, alipay
    status = Column(String(16), default="pending", nullable=False)  # pending, paid, cancelled, expired
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # 订单过期时间


class PricingPlan(Base):
    """套餐定价表"""
    __tablename__ = "pricing_plans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(String(32), unique=True, nullable=False, index=True)  # 如 pack_10
    name = Column(String(64), nullable=False)        # 如 "10次签名包"
    quota_count = Column(Integer, nullable=False)    # 签名次数
    price = Column(Integer, nullable=False)          # 价格（分）
    is_active = Column(Boolean, default=True)        # 是否上架
    sort_order = Column(Integer, default=0)          # 排序（越小越靠前）
    description = Column(String(256), nullable=True) # 套餐描述
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SignatureLog(Base):
    """签名记录表"""
    __tablename__ = "signature_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_key = Column(String(256), nullable=False, index=True)
    
    # 签名信息
    file_token = Column(String(128), nullable=True)
    file_name = Column(String(256), nullable=True)
    local_path = Column(Text, nullable=True)
    
    # 配额消耗
    quota_consumed = Column(Boolean, default=True, nullable=False)  # 是否消耗了配额
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SignForm(Base):
    """外部签名表单配置表"""
    __tablename__ = "sign_forms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    form_id = Column(String(32), unique=True, nullable=False, index=True)  # 表单唯一ID（用于URL）
    
    # 表单基本信息
    name = Column(String(100), nullable=False)  # 表单名称
    description = Column(Text, nullable=True)  # 表单描述
    
    # 关联的多维表格
    app_token = Column(String(64), nullable=False)  # 多维表格 app_token
    table_id = Column(String(64), nullable=False)  # 表格 ID
    signature_field_id = Column(String(64), nullable=False)  # 签名附件字段 ID
    
    # 额外表单字段配置 (JSON格式)
    # [{"field_id": "fld_xxx", "label": "姓名", "type": "text", "required": true}]
    extra_fields = Column(Text, nullable=True)
    
    # 创建者
    created_by = Column(String(256), nullable=True)  # user_key
    creator_refresh_token = Column(Text, nullable=True)  # 创建者的 refresh_token（用于外部表单提交）
    
    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # 过期时间（可选）
    
    # 提交统计
    submit_count = Column(Integer, default=0, nullable=False)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


def get_db():
    """获取数据库会话（FastAPI 依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（创建表）"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    # 直接运行此文件可初始化数据库
    init_db()
