"""
修复 admin_router.py 中剩余的 User 表引用
将所有用户查询改为使用 AppUserIdentity 表和用户独立数据库

执行方式：
cd backend
python scripts/fix_admin_router.py
"""
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

admin_router_path = os.path.join(BACKEND_DIR, "admin_router.py")

# 读取文件
with open(admin_router_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 update_user_quota
old_update_quota = '''    """调整用户配额 - 更新用户独立数据库中的配额"""
    user = db.query(AppUserIdentity).filter(AppUserIdentity.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.remaining_quota = req.remaining_quota
    db.commit()

    return {"success": True, "remaining_quota": user.remaining_quota}'''

new_update_quota = '''    """调整用户配额 - 更新用户独立数据库中的配额"""
    user = db.query(AppUserIdentity).filter(AppUserIdentity.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_key = f"{user.feishu_user_id}::{user.tenant_key}"
    ensure_user_database(user_key)
    user_db = get_user_session(user_key)
    
    try:
        profile = user_db.query(UserProfile).first()
        if not profile:
            raise HTTPException(status_code=404, detail="用户配置不存在")
        
        profile.remaining_quota = req.remaining_quota
        user_db.commit()
        
        return {"success": True, "remaining_quota": profile.remaining_quota}
    finally:
        user_db.close()'''

content = content.replace(old_update_quota, new_update_quota)

# 修复 delete_user
old_delete = '''    """删除用户及其关联记录"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db.delete(user)
    db.commit()'''

new_delete = '''    """删除用户及其关联记录"""
    user = db.query(AppUserIdentity).filter(AppUserIdentity.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 删除用户元信息
    db.delete(user)
    db.commit()
    
    # 注意：用户独立数据库不会被自动删除，需要手动清理
    return {"success": True}'''

content = content.replace(old_delete, new_delete)

# 修复 reset_user - 这个比较复杂，需要完整替换
old_reset_start = '''@router.post("/users/{user_id}/reset", summary="初始化/重置用户数据")
def reset_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """重置用户数据（包括配额、邀请码、已用次数等）"""
    user = db.query(User).filter(User.id == user_id).first()'''

new_reset_start = '''@router.post("/users/{user_id}/reset", summary="初始化/重置用户数据")
def reset_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """重置用户数据（包括配额、邀请码、已用次数等）"""
    user = db.query(AppUserIdentity).filter(AppUserIdentity.id == user_id).first()'''

content = content.replace(old_reset_start, new_reset_start)

# 修复 reset_user 中的 user.user_key
content = content.replace('ensure_user_database(user.user_key)', 'ensure_user_database(user_key)')
content = content.replace('user_db = get_user_session(user.user_key)', 'user_db = get_user_session(user_key)')
content = content.replace('if "::" in user.user_key:', 'if "::" in user_key:')
content = content.replace('open_id_val, tenant_key_val = user.user_key.split("::")', 'open_id_val, tenant_key_val = user_key.split("::")')
content = content.replace('print(f"Failed to reset user profile for {user.user_key}: {e}")', 'print(f"Failed to reset user profile for {user_key}: {e}")')

# 在 reset_user 函数开始处添加 user_key 定义
old_reset_body = '''    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 1. 处理旧的邀请码计数（如果需要）
    if user.invite_code_used:'''

new_reset_body = '''    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_key = f"{user.feishu_user_id}::{user.tenant_key}"

    # 1. 重置用户库状态
    try:'''

content = content.replace(old_reset_body, new_reset_body)

# 删除旧的邀请码处理和共享库重置逻辑
old_reset_end = '''    # 3. 重置共享库状态
    user.remaining_quota = 20
    user.total_used = 0
    user.invite_code_used = None
    user.invite_expire_at = None
    user.total_paid = 0
    
    db.commit()
    
    return {"success": True, "message": "用户数据已初始化"}'''

new_reset_end = '''    return {"success": True, "message": "用户数据已重置"}'''

content = content.replace(old_reset_end, new_reset_end)

# 修复 clear_user_invite
old_clear_invite = '''    """清理用户的邀请码使用记录"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not user.invite_code_used:
        return {"success": True, "message": "用户未使用过邀请码", "invite_code": None}

    invite_code_str = user.invite_code_used

    user.invite_code_used = None
    user.invite_expire_at = None

    invite = db.query(InviteCode).filter(InviteCode.code == invite_code_str).first()
    if invite and invite.used_count > 0:
        invite.used_count -= 1

    db.commit()

    return {
        "success": True,
        "message": "邀请码记录已清理",
        "invite_code": invite_code_str,
        "used_count_decreased": invite.used_count if invite else None,
    }'''

new_clear_invite = '''    """清理用户的邀请码使用记录"""
    user = db.query(AppUserIdentity).filter(AppUserIdentity.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_key = f"{user.feishu_user_id}::{user.tenant_key}"
    
    try:
        ensure_user_database(user_key)
        user_db = get_user_session(user_key)
        
        try:
            profile = user_db.query(UserProfile).first()
            if not profile or not profile.invite_code_used:
                return {"success": True, "message": "用户未使用过邀请码", "invite_code": None}
            
            invite_code_str = profile.invite_code_used
            
            # 清除用户的邀请码记录
            profile.invite_code_used = None
            profile.invite_expire_at = None
            user_db.commit()
            
            # 更新邀请码的使用计数（共享库）
            invite = db.query(InviteCode).filter(InviteCode.code == invite_code_str).first()
            if invite and invite.used_count > 0:
                invite.used_count -= 1
                db.commit()
            
            return {
                "success": True,
                "message": "邀请码记录已清理",
                "invite_code": invite_code_str,
                "used_count_decreased": invite.used_count if invite else None,
            }
        finally:
            user_db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")'''

content = content.replace(old_clear_invite, new_clear_invite)

# 修复 export_users
old_export = '''@router.get("/users/export", summary="导出用户 CSV")
def export_users(db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    users = db.query(User).all()'''

new_export = '''@router.get("/users/export", summary="导出用户 CSV")
def export_users(db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    users = db.query(AppUserIdentity).all()'''

content = content.replace(old_export, new_export)

# 修复 export_users 中的字段访问
content = content.replace('"open_id": u.open_id,', '"open_id": u.feishu_user_id,')
content = content.replace('u.open_id,', 'u.feishu_user_id,')

# 修复邀请码撤销功能中的用户查询
old_revoke = '''        affected_users = db.query(User).filter(User.invite_code_used == invite.code).all()
        for user in affected_users:
            # 1. 更新共享库 legacy 状态（保留原有逻辑）
            if user.invite_expire_at:
                user.invite_expire_at = None
                revoked_count += 1
            
            # 2. 更新独立用户库状态
            try:
                ensure_user_database(user.user_key)
                user_db = get_user_session(user.user_key)
                # 分解 open_id 和 tenant_key
                # user_key format: "open_id::tenant_key"
                if "::" in user.user_key:
                    open_id_val, tenant_key_val = user.user_key.split("::")'''

new_revoke = '''        # 查询所有使用该邀请码的用户（从用户独立数据库）
        affected_users = db.query(AppUserIdentity).all()
        for user in affected_users:
            user_key = f"{user.feishu_user_id}::{user.tenant_key}"
            
            try:
                ensure_user_database(user_key)
                user_db = get_user_session(user_key)
                
                if "::" in user_key:
                    open_id_val, tenant_key_val = user_key.split("::")'''

content = content.replace(old_revoke, new_revoke)

# 修复邀请码撤销中的错误日志
content = content.replace('print(f"Failed to revoke benefit for user {user.user_key}: {e}")', 'print(f"Failed to revoke benefit for user {user_key}: {e}")')

# 写回文件
with open(admin_router_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ admin_router.py 修复完成！")
print("")
print("修复内容：")
print("  - update_user_quota: 从用户独立数据库更新配额")
print("  - delete_user: 使用 AppUserIdentity 表")
print("  - reset_user: 使用 AppUserIdentity 表和用户独立数据库")
print("  - clear_user_invite: 从用户独立数据库清理邀请码")
print("  - export_users: 使用 AppUserIdentity 表")
print("  - 邀请码撤销: 遍历用户独立数据库")
