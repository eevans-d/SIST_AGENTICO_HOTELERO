import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
import uuid

from app.security.advanced_jwt_auth import AdvancedJWTAuth, UserRole
from app.models.user import User
from app.core.database import AsyncSessionFactory
from app.security.password_policy import get_password_policy
from sqlalchemy import select

@pytest.mark.asyncio
async def test_auth_db_integration():
    """
    Test authentication flow with real database and mocked Redis.
    """
    # 1. Setup
    # Mock Redis to avoid dependency
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    
    # Patch get_redis to return our mock
    with patch("app.security.advanced_jwt_auth.get_redis", new=AsyncMock(return_value=mock_redis)) as mock_get_redis:
        mock_get_redis.return_value = mock_redis
        
        auth_service = AdvancedJWTAuth()
        await auth_service.initialize()
        
        # 2. Create a test user in DB
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        password = "SecurePassword123!"
        email = f"{username}@example.com"
        
        pwd_policy = get_password_policy()
        hashed_password = pwd_policy.hash_password(password)
        
        user_id = str(uuid.uuid4())
        
        new_user = User(
            id=user_id,
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            password_last_changed=datetime.now(timezone.utc),
            password_must_change=False,
            failed_login_attempts=0
        )
        
        async with AsyncSessionFactory() as session:
            session.add(new_user)
            await session.commit()
            
        try:
            # 3. Authenticate
            session = await auth_service.authenticate_user(username, password)
            
            # 4. Verify
            assert session is not None
            assert session.user_id == user_id
            assert session.access_token is not None
            
            # Verify login stats updated (last_login should be set)
            async with AsyncSessionFactory() as db_session:
                user_db = await db_session.get(User, user_id)
                assert user_db.last_login is not None
                assert user_db.failed_login_attempts == 0
                
            # 5. Test invalid password
            failed_session = await auth_service.authenticate_user(username, "WrongPassword")
            assert failed_session is None
            
            # Verify failed attempts incremented
            async with AsyncSessionFactory() as db_session:
                # Need to refresh or get new session
                result = await db_session.execute(select(User).where(User.id == user_id)) # Need select import
                # Or just use get
                user_db = await db_session.get(User, user_id)
                assert user_db.failed_login_attempts == 1
                
        finally:
            # Cleanup
            async with AsyncSessionFactory() as session:
                user_to_delete = await session.get(User, user_id)
                if user_to_delete:
                    await session.delete(user_to_delete)
                    await session.commit()

# Need to import select for the verification part if I use execute
from sqlalchemy import select
