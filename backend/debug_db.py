import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add current directory to path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Order, Base, UserProfile
from user_db_manager import get_user_session

# --- Configuration ---
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "feishu")

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

print(f"Connecting to Shared DB: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
shared_db = SessionLocal()

print("\n=== Recent Orders (Last 10) ===")
orders = shared_db.query(Order).order_by(Order.created_at.desc()).limit(10).all()
for o in orders:
    print(f"Time: {o.created_at}, OrderID: {o.order_id}, Status: {o.status}, Amount: {o.amount}, UserKey: {o.user_key}")

print("\n=== User Databases Inspection ===")
# Scan 'users/' directory for sqlite files
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users")
if not os.path.exists(data_dir):
    print(f"User data directory not found: {data_dir}")
else:
    user_files = [f for f in os.listdir(data_dir) if f.startswith("feishu_user_") and f.endswith(".db")]
    print(f"Found {len(user_files)} user database files.")
    
    for db_file in user_files:
        user_key_hash = db_file.replace("feishu_user_", "").replace(".db", "")
        print(f"\nChecking DB: {db_file} (Hash: {user_key_hash})")
        
        # Use existing manager logic or direct connect
        db_path = os.path.join(data_dir, db_file)
        user_engine = create_engine(f"sqlite:///{db_path}")
        UserSession = sessionmaker(bind=user_engine)
        user_db = UserSession()
        
        try:
            profile = user_db.query(UserProfile).first()
            if profile:
                print(f"  -> Profile Found: OpenID={profile.open_id}, TenantKey={profile.tenant_key}")
                print(f"  -> Quota: Remaining={profile.remaining_quota}, TotalUsed={profile.total_used}, TotalPaid={profile.total_paid}")
                print(f"  -> Plan: {profile.current_plan_id}, Expires: {profile.plan_expires_at}")
            else:
                print("  -> No UserProfile found in this DB.")
        except Exception as e:
            print(f"  -> Error reading DB: {e}")
        finally:
            user_db.close()

shared_db.close()
