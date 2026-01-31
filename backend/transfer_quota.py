import os
import sys
import hashlib
from sqlalchemy import create_engine, text

# --- Configuration ---
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "18385828568ljs")

# Source: browser_test_user (feishu_user_94daadb0)
SOURCE_DB = "feishu_user_94daadb0"
# Target: Real User (feishu_user_1ef7bb28)
TARGET_DB = "feishu_user_1ef7bb28"

def get_engine(db_name):
    return create_engine(f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{db_name}?charset=utf8mb4")

print(f"=== Transferring Quota from {SOURCE_DB} to {TARGET_DB} ===")

source_data = {}

# 1. Read from Source
try:
    src_engine = get_engine(SOURCE_DB)
    with src_engine.connect() as conn:
        result = conn.execute(text("SELECT remaining_quota, total_paid, current_plan_id, plan_expires_at, is_unlimited FROM user_profile"))
        row = result.fetchone()
        if row:
            source_data = {
                "quota": row.remaining_quota,
                "paid": row.total_paid,
                "plan": row.current_plan_id,
                "expires": row.plan_expires_at,
                "unlimited": row.is_unlimited
            }
            print(f"Source Data Found: {source_data}")
        else:
            print("Source DB has no profile!")
            sys.exit(1)
except Exception as e:
    print(f"Failed to read source: {e}")
    sys.exit(1)

# 2. Update Target
if source_data:
    try:
        tgt_engine = get_engine(TARGET_DB)
        with tgt_engine.connect() as conn:
            # Update Quota & Plan
            conn.execute(text("""
                UPDATE user_profile 
                SET remaining_quota = :quota,
                    total_paid = total_paid + :paid,
                    current_plan_id = :plan,
                    plan_expires_at = :expires,
                    is_unlimited = :unlimited,
                    updated_at = NOW()
            """), source_data)
            conn.commit()
            print("Target DB Updated Successfully!")
            
            # Verify
            res = conn.execute(text("SELECT remaining_quota, current_plan_id FROM user_profile"))
            print(f"New Target State: {res.fetchone()}")
    except Exception as e:
        print(f"Failed to update target: {e}")
        sys.exit(1)

# 3. Reset Source (Optional but recommended to verify transfer)
    try:
        with src_engine.connect() as conn:
            conn.execute(text("""
                UPDATE user_profile 
                SET remaining_quota = 0, 
                    current_plan_id = NULL,
                    plan_expires_at = NULL,
                    is_unlimited = 0
            """))
            conn.commit()
            print("Source DB Reset (Quota moved).")
    except Exception as e:
        print(f"Warning: Failed to reset source: {e}")

print("\n=== Transfer Complete! ===")
