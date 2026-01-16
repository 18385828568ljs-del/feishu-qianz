#!/usr/bin/env python3
"""检查用户邀请码记录状态"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, User, InviteCode

db = SessionLocal()

try:
    # 检查所有用户
    users = db.query(User).all()
    print(f"总用户数: {len(users)}")
    
    users_with_invite = db.query(User).filter(User.invite_code_used.isnot(None)).all()
    print(f"使用过邀请码的用户数: {len(users_with_invite)}")
    
    if users_with_invite:
        print("\n使用过邀请码的用户:")
        for user in users_with_invite:
            print(f"  ID={user.id}, OpenID={user.open_id}, 邀请码={user.invite_code_used}")
    else:
        print("\n没有用户使用过邀请码")
    
    # 检查邀请码使用情况
    invites = db.query(InviteCode).all()
    print(f"\n邀请码总数: {len(invites)}")
    for invite in invites:
        print(f"  邀请码: {invite.code}, 已使用: {invite.used_count}/{invite.max_usage}")
        
finally:
    db.close()

