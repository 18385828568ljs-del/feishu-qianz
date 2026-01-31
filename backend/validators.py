"""
参数验证工具模块
提供统一的参数验证函数
"""
from typing import Optional
from fastapi import HTTPException


def validate_user_params(open_id: Optional[str], tenant_key: Optional[str], raise_error: bool = True) -> bool:
    """
    验证用户参数是否完整
    
    Args:
        open_id: 用户 open_id
        tenant_key: 租户 key
        raise_error: 是否在验证失败时抛出异常
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        HTTPException: 当 raise_error=True 且验证失败时
    """
    missing = []
    
    if not open_id or open_id.strip() == '':
        missing.append('open_id')
    
    if not tenant_key or tenant_key.strip() == '':
        missing.append('tenant_key')
    
    if missing:
        if raise_error:
            raise HTTPException(
                status_code=400,
                detail=f"缺少必填参数: {', '.join(missing)}"
            )
        return False
    
    return True


def validate_file_upload_params(
    open_id: Optional[str],
    tenant_key: Optional[str],
    file_name: Optional[str],
    folder_token: Optional[str],
    raise_error: bool = True
) -> bool:
    """
    验证文件上传参数是否完整
    
    Args:
        open_id: 用户 open_id
        tenant_key: 租户 key
        file_name: 文件名
        folder_token: 文件夹 token
        raise_error: 是否在验证失败时抛出异常
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        HTTPException: 当 raise_error=True 且验证失败时
    """
    missing = []
    
    if not open_id or open_id.strip() == '':
        missing.append('open_id')
    
    if not tenant_key or tenant_key.strip() == '':
        missing.append('tenant_key')
    
    if not file_name or file_name.strip() == '':
        missing.append('file_name')
    
    if not folder_token or folder_token.strip() == '':
        missing.append('folder_token')
    
    if missing:
        if raise_error:
            raise HTTPException(
                status_code=400,
                detail=f"缺少必填参数: {', '.join(missing)}"
            )
        return False
    
    return True


def validate_invite_code(code: Optional[str], raise_error: bool = True) -> bool:
    """
    验证邀请码参数
    
    Args:
        code: 邀请码
        raise_error: 是否在验证失败时抛出异常
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        HTTPException: 当 raise_error=True 且验证失败时
    """
    if not code or code.strip() == '':
        if raise_error:
            raise HTTPException(
                status_code=400,
                detail="邀请码不能为空"
            )
        return False
    
    return True


def validate_plan_id(plan_id: Optional[str], raise_error: bool = True) -> bool:
    """
    验证套餐ID参数
    
    Args:
        plan_id: 套餐ID
        raise_error: 是否在验证失败时抛出异常
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        HTTPException: 当 raise_error=True 且验证失败时
    """
    if not plan_id or plan_id.strip() == '':
        if raise_error:
            raise HTTPException(
                status_code=400,
                detail="套餐ID不能为空"
            )
        return False
    
    return True
