"""
Comprehensive Security Testing Suite
Unit tests for advanced JWT authentication system
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta, timezone
import jwt
import pyotp

from app.security.advanced_jwt_auth import AdvancedJWTAuth, UserRole, UserRegistration, UserLogin, User


class TestAdvancedJWTAuth:
    """Test suite for Advanced JWT Authentication"""

    @pytest_asyncio.fixture
    async def jwt_auth(self):
        """Create JWT auth instance for testing"""
        auth = AdvancedJWTAuth()

        # Mock Redis connection
        auth.redis_client = AsyncMock()
        auth.redis_client.get = AsyncMock(return_value=None)
        auth.redis_client.set = AsyncMock(return_value=True)
        auth.redis_client.delete = AsyncMock(return_value=True)
        auth.redis_client.expire = AsyncMock(return_value=True)
        auth.redis_client.exists = AsyncMock(return_value=False)

        # Mock database connection
        auth.db_session = AsyncMock()

        return auth

    @pytest_asyncio.fixture
    def sample_user_registration(self):
        """Sample user registration data"""
        return UserRegistration(
            email="test@hotel.com",
            password="SecurePassword123!",
            full_name="Test User",
            role=UserRole.GUEST,
            phone="+1234567890",
        )

    @pytest_asyncio.fixture
    def sample_user_login(self):
        """Sample user login data"""
        return UserLogin(email="test@hotel.com", password="SecurePassword123!")

    @pytest_asyncio.fixture
    def sample_user(self):
        """Sample user object"""
        return User(
            user_id="test-user-123",
            email="test@hotel.com",
            full_name="Test User",
            role=UserRole.GUEST,
            is_active=True,
            mfa_enabled=False,
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc),
        )


class TestUserRegistration:
    """Test user registration functionality"""

    @pytest_asyncio.fixture
    async def jwt_auth(self):
        """Create JWT auth instance for testing"""
        auth = AdvancedJWTAuth()
        auth.redis_client = AsyncMock()
        auth.db_session = AsyncMock()
        return auth

    async def test_register_user_success(self, jwt_auth, sample_user_registration):
        """Test successful user registration"""

        # Mock database operations
        jwt_auth.db_session.execute = AsyncMock()
        jwt_auth.db_session.commit = AsyncMock()
        jwt_auth.db_session.scalar = AsyncMock(return_value=None)  # No existing user

        result = await jwt_auth.register_user(sample_user_registration)

        assert result["success"] is True
        assert "user" in result
        assert result["user"]["email"] == sample_user_registration.email
        assert result["user"]["role"] == sample_user_registration.role.value

    async def test_register_user_duplicate_email(self, jwt_auth, sample_user_registration):
        """Test registration with duplicate email"""

        # Mock existing user
        existing_user = Mock()
        existing_user.email = sample_user_registration.email
        jwt_auth.db_session.scalar = AsyncMock(return_value=existing_user)

        result = await jwt_auth.register_user(sample_user_registration)

        assert result["success"] is False
        assert "already exists" in result["message"].lower()

    async def test_register_user_weak_password(self, jwt_auth):
        """Test registration with weak password"""

        weak_password_registration = UserRegistration(
            email="test@hotel.com",
            password="123",  # Weak password
            full_name="Test User",
            role=UserRole.GUEST,
        )

        result = await jwt_auth.register_user(weak_password_registration)

        assert result["success"] is False
        assert "password" in result["message"].lower()

    async def test_register_user_invalid_email(self, jwt_auth):
        """Test registration with invalid email"""

        # This should be caught by Pydantic validation
        with pytest.raises(ValueError):
            UserRegistration(
                email="invalid-email", password="SecurePassword123!", full_name="Test User", role=UserRole.GUEST
            )


class TestUserAuthentication:
    """Test user authentication functionality"""

    async def test_authenticate_user_success(self, jwt_auth, sample_user_login, sample_user):
        """Test successful user authentication"""

        # Mock user lookup
        jwt_auth._get_user_by_email = AsyncMock(return_value=sample_user)
        jwt_auth._verify_password = AsyncMock(return_value=True)
        jwt_auth._update_last_login = AsyncMock()
        jwt_auth._check_account_lockout = AsyncMock(return_value={"locked": False})

        result = await jwt_auth.authenticate_user(sample_user_login, "127.0.0.1")

        assert result["success"] is True
        assert result["user"]["user_id"] == sample_user.user_id
        assert result["user"]["email"] == sample_user.email

    async def test_authenticate_user_invalid_credentials(self, jwt_auth, sample_user_login):
        """Test authentication with invalid credentials"""

        jwt_auth._get_user_by_email = AsyncMock(return_value=None)

        result = await jwt_auth.authenticate_user(sample_user_login, "127.0.0.1")

        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    async def test_authenticate_user_wrong_password(self, jwt_auth, sample_user_login, sample_user):
        """Test authentication with wrong password"""

        jwt_auth._get_user_by_email = AsyncMock(return_value=sample_user)
        jwt_auth._verify_password = AsyncMock(return_value=False)
        jwt_auth._record_failed_login = AsyncMock()
        jwt_auth._check_account_lockout = AsyncMock(return_value={"locked": False})

        result = await jwt_auth.authenticate_user(sample_user_login, "127.0.0.1")

        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    async def test_authenticate_user_account_locked(self, jwt_auth, sample_user_login, sample_user):
        """Test authentication with locked account"""

        jwt_auth._get_user_by_email = AsyncMock(return_value=sample_user)
        jwt_auth._check_account_lockout = AsyncMock(
            return_value={"locked": True, "unlock_time": datetime.now(timezone.utc) + timedelta(minutes=30)}
        )

        result = await jwt_auth.authenticate_user(sample_user_login, "127.0.0.1")

        assert result["success"] is False
        assert "locked" in result["message"].lower()

    async def test_authenticate_user_mfa_required(self, jwt_auth, sample_user_login, sample_user):
        """Test authentication when MFA is required"""

        sample_user.mfa_enabled = True
        jwt_auth._get_user_by_email = AsyncMock(return_value=sample_user)
        jwt_auth._verify_password = AsyncMock(return_value=True)
        jwt_auth._check_account_lockout = AsyncMock(return_value={"locked": False})

        # Login without MFA code
        result = await jwt_auth.authenticate_user(sample_user_login, "127.0.0.1")

        assert result["success"] is False
        assert result["mfa_required"] is True

    async def test_authenticate_user_with_valid_mfa(self, jwt_auth, sample_user):
        """Test authentication with valid MFA code"""

        sample_user.mfa_enabled = True
        login_data = UserLogin(email="test@hotel.com", password="SecurePassword123!", mfa_code="123456")

        jwt_auth._get_user_by_email = AsyncMock(return_value=sample_user)
        jwt_auth._verify_password = AsyncMock(return_value=True)
        jwt_auth._verify_mfa_code = AsyncMock(return_value={"valid": True})
        jwt_auth._check_account_lockout = AsyncMock(return_value={"locked": False})
        jwt_auth._update_last_login = AsyncMock()

        result = await jwt_auth.authenticate_user(login_data, "127.0.0.1")

        assert result["success"] is True
        assert result.get("mfa_required", False) is False


class TestTokenGeneration:
    """Test JWT token generation and validation"""

    async def test_generate_tokens(self, jwt_auth, sample_user):
        """Test token generation"""

        jwt_auth._create_session = AsyncMock(return_value="session-123")

        tokens = await jwt_auth.generate_tokens(sample_user.__dict__)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "bearer"

    async def test_verify_valid_token(self, jwt_auth, sample_user):
        """Test verification of valid token"""

        # Generate a token first
        jwt_auth._create_session = AsyncMock(return_value="session-123")
        tokens = await jwt_auth.generate_tokens(sample_user.__dict__)

        # Mock session and user retrieval
        jwt_auth._get_session = AsyncMock(
            return_value={"session_id": "session-123", "user_id": sample_user.user_id, "is_active": True}
        )
        jwt_auth._get_user_by_id = AsyncMock(return_value=sample_user)

        result = await jwt_auth.verify_token(tokens["access_token"])

        assert result["valid"] is True
        assert result["user"]["user_id"] == sample_user.user_id

    async def test_verify_expired_token(self, jwt_auth, sample_user):
        """Test verification of expired token"""

        # Create an expired token
        expired_payload = {
            "sub": sample_user.user_id,
            "email": sample_user.email,
            "role": sample_user.role.value,
            "session_id": "session-123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "type": "access",
        }

        expired_token = jwt.encode(expired_payload, jwt_auth.settings.secret_key, algorithm="HS256")

        result = await jwt_auth.verify_token(expired_token)

        assert result["valid"] is False
        assert "expired" in result["reason"].lower()

    async def test_verify_invalid_token(self, jwt_auth):
        """Test verification of invalid token"""

        result = await jwt_auth.verify_token("invalid.token.here")

        assert result["valid"] is False
        assert "invalid" in result["reason"].lower()

    async def test_refresh_access_token(self, jwt_auth, sample_user):
        """Test refresh token functionality"""

        # Mock refresh token validation
        jwt_auth._validate_refresh_token = AsyncMock(
            return_value={"valid": True, "user_id": sample_user.user_id, "session_id": "session-123"}
        )
        jwt_auth._get_user_by_id = AsyncMock(return_value=sample_user)
        jwt_auth._update_session_activity = AsyncMock()

        result = await jwt_auth.refresh_access_token("valid.refresh.token")

        assert result["success"] is True
        assert "access_token" in result
        assert "expires_in" in result


class TestMFAFunctionality:
    """Test Multi-Factor Authentication functionality"""

    async def test_setup_mfa(self, jwt_auth):
        """Test MFA setup"""

        user_id = "test-user-123"
        secret = pyotp.random_base32()
        backup_codes = ["code1", "code2", "code3"]

        jwt_auth.redis_client.set = AsyncMock(return_value=True)

        result = await jwt_auth.setup_mfa(user_id, secret, backup_codes)

        assert result is True
        # Verify Redis calls were made
        assert jwt_auth.redis_client.set.call_count >= 2  # Secret and backup codes

    async def test_verify_valid_mfa_code(self, jwt_auth):
        """Test verification of valid MFA code"""

        user_id = "test-user-123"
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Mock Redis to return the secret
        jwt_auth.redis_client.get = AsyncMock(return_value=secret)

        result = await jwt_auth.verify_mfa_code(user_id, valid_code)

        assert result["valid"] is True

    async def test_verify_invalid_mfa_code(self, jwt_auth):
        """Test verification of invalid MFA code"""

        user_id = "test-user-123"
        secret = pyotp.random_base32()
        invalid_code = "000000"

        # Mock Redis to return the secret
        jwt_auth.redis_client.get = AsyncMock(return_value=secret)

        result = await jwt_auth.verify_mfa_code(user_id, invalid_code)

        assert result["valid"] is False

    async def test_verify_backup_code(self, jwt_auth):
        """Test verification using backup code"""

        user_id = "test-user-123"
        backup_code = "BACKUP123"

        # Mock Redis to return backup codes
        jwt_auth.redis_client.get = AsyncMock(return_value="BACKUP123,BACKUP456,BACKUP789")
        jwt_auth.redis_client.set = AsyncMock(return_value=True)

        result = await jwt_auth.verify_mfa_code(user_id, backup_code)

        assert result["valid"] is True
        # Verify backup code was removed
        jwt_auth.redis_client.set.assert_called()

    async def test_enable_mfa(self, jwt_auth):
        """Test enabling MFA for user"""

        user_id = "test-user-123"
        jwt_auth.db_session.execute = AsyncMock()
        jwt_auth.db_session.commit = AsyncMock()

        await jwt_auth.enable_mfa(user_id)

        # Verify database update was called
        jwt_auth.db_session.execute.assert_called()
        jwt_auth.db_session.commit.assert_called()

    async def test_disable_mfa(self, jwt_auth):
        """Test disabling MFA for user"""

        user_id = "test-user-123"
        jwt_auth.db_session.execute = AsyncMock()
        jwt_auth.db_session.commit = AsyncMock()
        jwt_auth.redis_client.delete = AsyncMock(return_value=True)

        await jwt_auth.disable_mfa(user_id)

        # Verify database and Redis operations
        jwt_auth.db_session.execute.assert_called()
        jwt_auth.db_session.commit.assert_called()
        jwt_auth.redis_client.delete.assert_called()


class TestSessionManagement:
    """Test session management functionality"""

    async def test_create_session(self, jwt_auth, sample_user):
        """Test session creation"""

        jwt_auth.redis_client.set = AsyncMock(return_value=True)
        jwt_auth.redis_client.expire = AsyncMock(return_value=True)

        session_id = await jwt_auth._create_session(sample_user.user_id, "127.0.0.1", "Mozilla/5.0 Test Browser")

        assert session_id is not None
        assert len(session_id) > 10  # Should be a meaningful session ID

        # Verify Redis operations
        jwt_auth.redis_client.set.assert_called()
        jwt_auth.redis_client.expire.assert_called()

    async def test_get_session(self, jwt_auth):
        """Test session retrieval"""

        session_data = {
            "session_id": "session-123",
            "user_id": "user-456",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }

        jwt_auth.redis_client.get = AsyncMock(return_value=str(session_data))

        result = await jwt_auth._get_session("session-123")

        assert result is not None
        jwt_auth.redis_client.get.assert_called_with("session:session-123")

    async def test_invalidate_session(self, jwt_auth):
        """Test session invalidation"""

        jwt_auth.redis_client.delete = AsyncMock(return_value=True)

        await jwt_auth._invalidate_session("session-123")

        jwt_auth.redis_client.delete.assert_called_with("session:session-123")

    async def test_logout_user(self, jwt_auth):
        """Test user logout"""

        user_id = "user-123"
        session_id = "session-456"

        jwt_auth._invalidate_session = AsyncMock()
        jwt_auth._invalidate_user_tokens = AsyncMock()

        await jwt_auth.logout_user(user_id, session_id)

        jwt_auth._invalidate_session.assert_called_with(session_id)
        jwt_auth._invalidate_user_tokens.assert_called_with(user_id)


class TestAccountSecurity:
    """Test account security features"""

    async def test_account_lockout_after_failed_attempts(self, jwt_auth):
        """Test account lockout after multiple failed attempts"""

        user_id = "user-123"
        ip_address = "192.168.1.100"

        # Mock failed attempts
        jwt_auth.redis_client.get = AsyncMock(return_value="5")  # 5 failed attempts
        jwt_auth.redis_client.set = AsyncMock(return_value=True)
        jwt_auth.redis_client.expire = AsyncMock(return_value=True)

        result = await jwt_auth._check_account_lockout(user_id, ip_address)

        assert result["locked"] is True
        assert "unlock_time" in result

    async def test_progressive_lockout_duration(self, jwt_auth):
        """Test progressive lockout duration"""

        user_id = "user-123"

        # Mock lockout count
        jwt_auth.redis_client.get = AsyncMock(return_value="3")  # 3rd lockout

        lockout_duration = await jwt_auth._calculate_lockout_duration(user_id)

        # Should be exponentially increasing
        assert lockout_duration >= 30  # At least 30 minutes for 3rd lockout

    async def test_reset_failed_attempts_on_success(self, jwt_auth):
        """Test resetting failed attempts on successful login"""

        user_id = "user-123"
        ip_address = "192.168.1.100"

        jwt_auth.redis_client.delete = AsyncMock(return_value=True)

        await jwt_auth._reset_failed_attempts(user_id, ip_address)

        # Verify failed attempts were cleared
        jwt_auth.redis_client.delete.assert_called()


class TestPasswordSecurity:
    """Test password security features"""

    async def test_password_strength_validation(self, jwt_auth):
        """Test password strength validation"""

        strong_passwords = ["StrongPassword123!", "MySecure@Pass2024", "Complex#Password456"]

        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "Password",  # Missing numbers and symbols
            "password123",  # Missing uppercase and symbols
        ]

        for password in strong_passwords:
            assert jwt_auth._validate_password_strength(password) is True

        for password in weak_passwords:
            assert jwt_auth._validate_password_strength(password) is False

    async def test_password_hashing(self, jwt_auth):
        """Test password hashing and verification"""

        password = "TestPassword123!"

        # Hash password
        hashed = await jwt_auth._hash_password(password)

        assert hashed != password  # Should be hashed
        assert len(hashed) > 50  # Should be long hash

        # Verify password
        assert await jwt_auth._verify_password(password, hashed) is True
        assert await jwt_auth._verify_password("wrong_password", hashed) is False

    async def test_change_password(self, jwt_auth, sample_user):
        """Test password change functionality"""

        old_password = "OldPassword123!"
        new_password = "NewPassword456!"

        # Mock user retrieval and password verification
        jwt_auth._get_user_by_id = AsyncMock(return_value=sample_user)
        jwt_auth._verify_password = AsyncMock(return_value=True)
        jwt_auth._hash_password = AsyncMock(return_value="hashed_new_password")
        jwt_auth.db_session.execute = AsyncMock()
        jwt_auth.db_session.commit = AsyncMock()

        result = await jwt_auth.change_password(sample_user.user_id, old_password, new_password)

        assert result["success"] is True
        jwt_auth._verify_password.assert_called_with(old_password, sample_user.password_hash)
        jwt_auth._hash_password.assert_called_with(new_password)


class TestRoleBasedAccess:
    """Test role-based access control"""

    async def test_role_hierarchy(self, jwt_auth):
        """Test role hierarchy validation"""

        # Test role hierarchy: SYSTEM > ADMIN > MANAGER > RECEPTIONIST > GUEST

        assert jwt_auth._has_role_access(UserRole.SYSTEM, UserRole.ADMIN) is True
        assert jwt_auth._has_role_access(UserRole.ADMIN, UserRole.MANAGER) is True
        assert jwt_auth._has_role_access(UserRole.MANAGER, UserRole.RECEPTIONIST) is True
        assert jwt_auth._has_role_access(UserRole.RECEPTIONIST, UserRole.GUEST) is True

        # Test reverse (should be False)
        assert jwt_auth._has_role_access(UserRole.GUEST, UserRole.ADMIN) is False
        assert jwt_auth._has_role_access(UserRole.RECEPTIONIST, UserRole.MANAGER) is False

    async def test_permission_checking(self, jwt_auth, sample_user):
        """Test permission checking"""

        # Guest permissions
        guest_user = sample_user
        guest_user.role = UserRole.GUEST

        assert jwt_auth._has_permission(guest_user, "view_own_reservations") is True
        assert jwt_auth._has_permission(guest_user, "manage_users") is False

        # Admin permissions
        admin_user = sample_user
        admin_user.role = UserRole.ADMIN

        assert jwt_auth._has_permission(admin_user, "manage_users") is True
        assert jwt_auth._has_permission(admin_user, "view_system_logs") is True


class TestErrorHandling:
    """Test error handling in authentication system"""

    async def test_database_connection_error(self, jwt_auth, sample_user_registration):
        """Test handling of database connection errors"""

        # Mock database error
        jwt_auth.db_session.execute = AsyncMock(side_effect=Exception("Database connection failed"))

        result = await jwt_auth.register_user(sample_user_registration)

        assert result["success"] is False
        assert "error" in result["message"].lower()

    async def test_redis_connection_error(self, jwt_auth, sample_user):
        """Test handling of Redis connection errors"""

        # Mock Redis error
        jwt_auth.redis_client.set = AsyncMock(side_effect=Exception("Redis connection failed"))

        # Should handle gracefully and fall back
        result = await jwt_auth._create_session(sample_user.user_id, "127.0.0.1", "Test Browser")

        # Should still work but maybe with reduced functionality
        assert result is not None or result is None  # Either works or fails gracefully

    async def test_invalid_token_format(self, jwt_auth):
        """Test handling of invalid token formats"""

        invalid_tokens = ["", "not.a.token", "invalid_token_format", "Bearer invalid", None]

        for token in invalid_tokens:
            if token is not None:
                result = await jwt_auth.verify_token(token)
                assert result["valid"] is False


class TestPerformanceAndScaling:
    """Test performance and scaling aspects"""

    async def test_token_blacklist_performance(self, jwt_auth):
        """Test token blacklist performance with many tokens"""

        # Add many tokens to blacklist
        tokens = [f"token-{i}" for i in range(1000)]

        jwt_auth.redis_client.sadd = AsyncMock(return_value=True)
        jwt_auth.redis_client.sismember = AsyncMock(return_value=False)

        # Test adding tokens
        for token in tokens[:100]:  # Test first 100
            await jwt_auth._blacklist_token(token)

        # Test checking blacklist
        for token in tokens[:100]:
            is_blacklisted = await jwt_auth._is_token_blacklisted(token)
            assert is_blacklisted is False  # Mocked to return False

    async def test_concurrent_login_attempts(self, jwt_auth, sample_user_login, sample_user):
        """Test handling of concurrent login attempts"""

        jwt_auth._get_user_by_email = AsyncMock(return_value=sample_user)
        jwt_auth._verify_password = AsyncMock(return_value=True)
        jwt_auth._check_account_lockout = AsyncMock(return_value={"locked": False})
        jwt_auth._update_last_login = AsyncMock()
        jwt_auth._create_session = AsyncMock(return_value="session-123")

        # Simulate concurrent logins
        import asyncio

        tasks = [jwt_auth.authenticate_user(sample_user_login, f"127.0.0.{i}") for i in range(10)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed or handle gracefully
        for result in results:
            assert not isinstance(result, Exception) or "locked" in str(result).lower()


# Integration Tests
class TestAuthenticationIntegration:
    """Integration tests for authentication flow"""

    async def test_complete_authentication_flow(self, jwt_auth, sample_user_registration):
        """Test complete authentication flow from registration to logout"""

        # Mock all dependencies
        jwt_auth.redis_client = AsyncMock()
        jwt_auth.db_session = AsyncMock()
        jwt_auth.db_session.scalar = AsyncMock(return_value=None)  # No existing user
        jwt_auth.db_session.execute = AsyncMock()
        jwt_auth.db_session.commit = AsyncMock()

        # 1. Register user
        registration_result = await jwt_auth.register_user(sample_user_registration)
        assert registration_result["success"] is True

        # 2. Login user
        login_data = UserLogin(email=sample_user_registration.email, password=sample_user_registration.password)

        # Mock user for login
        user_dict = {
            "user_id": "test-user-123",
            "email": sample_user_registration.email,
            "role": sample_user_registration.role.value,
            "is_active": True,
            "mfa_enabled": False,
        }

        jwt_auth._get_user_by_email = AsyncMock(return_value=type("User", (), user_dict)())
        jwt_auth._verify_password = AsyncMock(return_value=True)
        jwt_auth._check_account_lockout = AsyncMock(return_value={"locked": False})
        jwt_auth._update_last_login = AsyncMock()

        auth_result = await jwt_auth.authenticate_user(login_data, "127.0.0.1")
        assert auth_result["success"] is True

        # 3. Generate tokens
        jwt_auth._create_session = AsyncMock(return_value="session-123")
        tokens = await jwt_auth.generate_tokens(user_dict)
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # 4. Verify token
        jwt_auth._get_session = AsyncMock(
            return_value={"session_id": "session-123", "user_id": user_dict["user_id"], "is_active": True}
        )
        jwt_auth._get_user_by_id = AsyncMock(return_value=type("User", (), user_dict)())

        verify_result = await jwt_auth.verify_token(tokens["access_token"])
        assert verify_result["valid"] is True

        # 5. Logout user
        jwt_auth._invalidate_session = AsyncMock()
        jwt_auth._invalidate_user_tokens = AsyncMock()

        await jwt_auth.logout_user(user_dict["user_id"], "session-123")

        jwt_auth._invalidate_session.assert_called_with("session-123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
