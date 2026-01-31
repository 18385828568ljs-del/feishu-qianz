import os
import sys
import hashlib
from sqlalchemy import create_engine, text
from datetime import datetime

# --- Configuration ---
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "18385828568ljs") # Hardcoded from debug output
MASTER_DB_NAME = "feishu_master"
SHARED_DB_NAME = "feishu" # Old shared DB

# Helper to get engine
def get_engine(db_name):
    return create_engine(f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{db_name}?charset=utf8mb4")

def get_db_name(user_key):
    hash_value = hashlib.md5(user_key.encode()).hexdigest()[:8]
    return f"feishu_user_{hash_value}"

print("\n=== 1. Checking Shared DB (Orders) ===")
try:
    engine = get_engine(SHARED_DB_NAME)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT created_at, order_id, status, amount, user_key FROM orders ORDER BY created_at DESC LIMIT 5"))
        for row in result:
            print(f"Order: {row.created_at} | {row.order_id} | {row.status} | {row.amount} | {row.user_key}")
except Exception as e:
    print(f"Error checking shared DB: {e}")

print("\n=== 2. Checking Master DB (User Mapping) ===")
user_dbs = {}
try:
    engine = get_engine(MASTER_DB_NAME)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT user_key, db_name, open_id FROM user_databases"))
        print(f"Found {result.rowcount} registered user databases.")
        for row in result:
            user_dbs[row.user_key] = row.db_name
            print(f"Map: {row.user_key} -> {row.db_name}")
except Exception as e:
    print(f"Error checking master DB: {e}")

print("\n=== 3. Checking Target User Profiles ===")
# key1: browser_test_user::browser_test_tenant
# key2: ou_b31756a18c7f43f29734f9e7bd79e8e3::145b59171ac65740

target_keys = [
    "browser_test_user::browser_test_tenant",
    "ou_b31756a18c7f43f29734f9e7bd79e8e3::145b59171ac65740"
]

for key in target_keys:
    print(f"\nScanning for user_key: {key}")
    db_name = user_dbs.get(key)
    if not db_name:
        # Fallback: calculate what it SHOULD be
        db_name = get_db_name(key)
        print(f"  -> Not in registry, calculating expected DB name: {db_name}")
    else:
        print(f"  -> Found in registry: {db_name}")
    
    try:
        user_engine = get_engine(db_name)
        with user_engine.connect() as conn:
            # Check if DB exists by trying to query
            try:
                res = conn.execute(text("SELECT remaining_quota, total_used, total_paid, current_plan_id FROM user_profile"))
                row = res.fetchone()
                if row:
                    print(f"  -> [DATA FOUND] Quota: {row.remaining_quota}, Used: {row.total_used}, Paid: {row.total_paid}, Plan: {row.current_plan_id}")
                else:
                    print(f"  -> Profile table empty.")
            except Exception as inner_e:
                print(f"  -> Error querying profile (DB might not exist): {inner_e}")
    except Exception as e:
        print(f"  -> Connection failed: {e}")
