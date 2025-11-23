"""
Seed initial admin user to Supabase database
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import datetime, timezone

from app.core.database import AsyncSessionFactory
from app.models.user import User, UserRole
from app.security.password_policy import get_password_policy

async def seed_admin():
    """Create initial admin user"""
    
    # Admin credentials
    username = "admin"
    password = "admin123!"  # CHANGE THIS IN PRODUCTION
    email = "admin@hotelagenteia.com"
    
    print("🌱 Seeding admin user...")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print()
    
    # Hash password
    pwd_policy = get_password_policy()
    hashed_password = pwd_policy.hash_password(password)
    
    # Create user
    admin_user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=UserRole.ADMIN,
        full_name="System Administrator",
        is_active=True,
        is_superuser=True,
        is_verified=True,
        mfa_enabled=False,
        failed_login_attempts=0,
        last_login=None,
        account_locked_until=None,
        password_last_changed=datetime.now(timezone.utc),
        password_must_change=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        tenant_id=None
    )
    
    try:
        async with AsyncSessionFactory() as session:
            # Check if admin already exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.username == username)
            )
            existing = result.scalars().first()
            
            if existing:
                print(f"⚠️  Admin user '{username}' already exists (ID: {existing.id})")
                print("   Skipping creation.")
                return
            
            # Insert new admin
            session.add(admin_user)
            await session.commit()
            
            print(f"✅ Admin user created successfully!")
            print(f"   ID: {admin_user.id}")
            print()
            print("🔐 You can now login with:")
            print(f"   curl -X POST http://localhost:8000/api/v1/auth/login \\")
            print(f"     -H 'Content-Type: application/json' \\")
            print(f"     -d '{{\"username\":\"{username}\",\"password\":\"{password}\"}}'")
            print()
            print("⚠️  IMPORTANT: Change the password immediately in production!")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(seed_admin())
