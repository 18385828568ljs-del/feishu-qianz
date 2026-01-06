"""
统一错误处理模块
定义错误码和标准化错误响应格式
"""
from enum import Enum
from typing import Optional, Any
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(Enum):
    """错误码枚举"""
    # 通用错误 (1000-1099)
    SUCCESS = 0
    UNKNOWN_ERROR = 1000
    INVALID_PARAMS = 1001
    UNAUTHORIZED = 1002
    FORBIDDEN = 1003
    NOT_FOUND = 1004
    
    # 用户/配额相关 (1100-1199)
    NO_QUOTA = 1100
    QUOTA_EXPIRED = 1101
    USER_NOT_FOUND = 1102
    
    # 邀请码相关 (1200-1299)
    INVITE_CODE_INVALID = 1200
    INVITE_CODE_EXPIRED = 1201
    INVITE_CODE_USED = 1202
    
    # 表单相关 (1300-1399)
    FORM_NOT_FOUND = 1300
    FORM_EXPIRED = 1301
    FORM_FIELD_ERROR = 1302
    
    # 文件/上传相关 (1400-1499)
    FILE_UPLOAD_FAILED = 1400
    FILE_TOO_LARGE = 1401
    FILE_TYPE_NOT_ALLOWED = 1402
    EMPTY_FILE = 1403
    
    # 飞书API相关 (1500-1599)
    FEISHU_API_ERROR = 1500
    FEISHU_AUTH_FAILED = 1501
    FEISHU_TOKEN_EXPIRED = 1502
    
    # 数据库相关 (1600-1699)
    DB_ERROR = 1600
    DB_NOT_AVAILABLE = 1601


# 错误码对应的 HTTP 状态码
ERROR_STATUS_MAP = {
    ErrorCode.SUCCESS: 200,
    ErrorCode.UNKNOWN_ERROR: 500,
    ErrorCode.INVALID_PARAMS: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.NO_QUOTA: 402,
    ErrorCode.QUOTA_EXPIRED: 402,
    ErrorCode.INVITE_CODE_INVALID: 400,
    ErrorCode.INVITE_CODE_EXPIRED: 400,
    ErrorCode.INVITE_CODE_USED: 400,
    ErrorCode.FORM_NOT_FOUND: 404,
    ErrorCode.FORM_EXPIRED: 410,
    ErrorCode.FILE_UPLOAD_FAILED: 500,
    ErrorCode.EMPTY_FILE: 400,
    ErrorCode.FEISHU_API_ERROR: 502,
    ErrorCode.DB_ERROR: 500,
}

# 错误码对应的中文消息
ERROR_MSG_MAP = {
    ErrorCode.SUCCESS: "成功",
    ErrorCode.UNKNOWN_ERROR: "未知错误",
    ErrorCode.INVALID_PARAMS: "参数错误",
    ErrorCode.UNAUTHORIZED: "未授权",
    ErrorCode.FORBIDDEN: "无权限",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.NO_QUOTA: "配额不足",
    ErrorCode.QUOTA_EXPIRED: "配额已过期",
    ErrorCode.USER_NOT_FOUND: "用户不存在",
    ErrorCode.INVITE_CODE_INVALID: "邀请码无效",
    ErrorCode.INVITE_CODE_EXPIRED: "邀请码已过期",
    ErrorCode.INVITE_CODE_USED: "邀请码已被使用",
    ErrorCode.FORM_NOT_FOUND: "表单不存在",
    ErrorCode.FORM_EXPIRED: "表单已过期",
    ErrorCode.FORM_FIELD_ERROR: "表单字段错误",
    ErrorCode.FILE_UPLOAD_FAILED: "文件上传失败",
    ErrorCode.FILE_TOO_LARGE: "文件过大",
    ErrorCode.FILE_TYPE_NOT_ALLOWED: "不支持的文件类型",
    ErrorCode.EMPTY_FILE: "文件为空",
    ErrorCode.FEISHU_API_ERROR: "飞书API调用失败",
    ErrorCode.FEISHU_AUTH_FAILED: "飞书授权失败",
    ErrorCode.FEISHU_TOKEN_EXPIRED: "飞书令牌已过期",
    ErrorCode.DB_ERROR: "数据库错误",
    ErrorCode.DB_NOT_AVAILABLE: "数据库不可用",
}


class ErrorResponse(BaseModel):
    """统一错误响应格式"""
    code: int
    message: str
    details: Optional[Any] = None


class AppException(Exception):
    """应用自定义异常"""
    def __init__(
        self, 
        error_code: ErrorCode, 
        message: str = None,
        details: Any = None
    ):
        self.error_code = error_code
        self.message = message or ERROR_MSG_MAP.get(error_code, "未知错误")
        self.details = details
        self.status_code = ERROR_STATUS_MAP.get(error_code, 500)
        super().__init__(self.message)


def create_error_response(
    error_code: ErrorCode,
    message: str = None,
    details: Any = None
) -> JSONResponse:
    """创建统一格式的错误响应"""
    status_code = ERROR_STATUS_MAP.get(error_code, 500)
    msg = message or ERROR_MSG_MAP.get(error_code, "未知错误")
    
    return JSONResponse(
        status_code=status_code,
        content={
            "code": error_code.value,
            "message": msg,
            "details": details
        }
    )


def create_success_response(data: Any = None, message: str = "成功") -> dict:
    """创建统一格式的成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data
    }


async def app_exception_handler(request: Request, exc: AppException):
    """AppException 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.error_code.value,
            "message": exc.message,
            "details": exc.details
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "code": ErrorCode.UNKNOWN_ERROR.value,
            "message": "服务器内部错误",
            "details": str(exc) if str(exc) else None
        }
    )
