"""
Tests for Password Policy Enforcement
======================================

Tests password strength validation, history enforcement, and rotation checks.

Author: Backend AI Team
Date: 2025-11-03
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.security.password_policy import (
    PasswordPolicy,
    PasswordPolicyViolation,
    get_password_policy,
)
from app.models.user import User, PasswordHistory, Base


@pytest_asyncio.fixture
async def db_session():
    """Create in-memory SQLite database for testing"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionFactory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionFactory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def password_policy():
    """Create password policy instance for testing"""
    return PasswordPolicy(
        min_length=12,
        require_uppercase=True,
        require_lowercase=True,
        require_digit=True,
        require_special=True,
        history_size=5,
        rotation_days=90,
    )


class TestPasswordStrength:
    """Test password strength validation"""

    def test_valid_password(self, password_policy):
        """Test that valid password passes all checks"""
        password = "SecureP@ssw0rd123"
        is_valid, violations = password_policy.validate_password_strength(password)

        assert is_valid is True
        assert len(violations) == 0

    def test_too_short(self, password_policy):
        """Test password length requirement"""
        password = "Short1!"
        is_valid, violations = password_policy.validate_password_strength(password)

        assert is_valid is False
        assert any("12 characters" in v for v in violations)

    def test_no_uppercase(self, password_policy):
        """Test uppercase requirement"""
        password = "lowercase123!@#"
        is_valid, violations = password_policy.validate_password_strength(password)

        assert is_valid is False
        assert any("uppercase" in v for v in violations)

    def test_no_lowercase(self, password_policy):
        """Test lowercase requirement"""
        password = "UPPERCASE123!@#"
        is_valid, violations = password_policy.validate_password_strength(password)

        assert is_valid is False
        assert any("lowercase" in v for v in violations)

    def test_no_digit(self, password_policy):
        """Test digit requirement"""
        password = "NoDigitsHere!@#"
        is_valid, violations = password_policy.validate_password_strength(password)

        assert is_valid is False
        assert any("digit" in v for v in violations)

    def test_no_special(self, password_policy):
        """Test special character requirement"""
        password = "NoSpecialChar123"
        is_valid, violations = password_policy.validate_password_strength(password)

        assert is_valid is False
        assert any("special character" in v for v in violations)

    def test_multiple_violations(self, password_policy):
        """Test password with multiple violations"""
        password = "weak"
        is_valid, violations = password_policy.validate_password_strength(password)

        assert is_valid is False
        assert len(violations) >= 3  # Should have multiple errors


class TestPasswordHistory:
    """Test password history enforcement"""

    @pytest.mark.asyncio
    async def test_new_user_no_history(self, password_policy, db_session):
        """Test that new users have no history conflicts"""
        is_valid, error = await password_policy.validate_password_history(
            db_session, "new_user_123", "NewP@ssw0rd123"
        )

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_password_reuse_detected(self, password_policy, db_session):
        """Test that password reuse is detected"""
        user_id = "test_user_456"
        password = "ReusedP@ssw0rd123"

        # Create user
        user = User(
            id=user_id,
            username="testuser",
            email="test@example.com",
            hashed_password=password_policy.hash_password(password),
        )
        db_session.add(user)

        # Add password to history
        history_entry = PasswordHistory(
            user_id=user_id,
            password_hash=password_policy.hash_password(password),
        )
        db_session.add(history_entry)
        await db_session.commit()

        # Try to reuse same password
        is_valid, error = await password_policy.validate_password_history(
            db_session, user_id, password
        )

        assert is_valid is False
        assert error is not None
        assert "Cannot reuse" in error

    @pytest.mark.asyncio
    async def test_old_password_allowed_after_history_size(self, password_policy, db_session):
        """Test that passwords older than history_size can be reused"""
        user_id = "test_user_789"
        old_password = "OldP@ssw0rd123"

        # Create user
        user = User(
            id=user_id,
            username="testuser2",
            email="test2@example.com",
            hashed_password=password_policy.hash_password("CurrentP@ssw0rd"),
        )
        db_session.add(user)

        # Add 5 recent passwords (history_size=5)
        for i in range(5):
            history_entry = PasswordHistory(
                user_id=user_id,
                password_hash=password_policy.hash_password(f"RecentP@ss{i}"),
                created_at=datetime.utcnow() - timedelta(days=i*20),
            )
            db_session.add(history_entry)

        await db_session.commit()

        # Old password (not in recent 5) should be allowed
        is_valid, error = await password_policy.validate_password_history(
            db_session, user_id, old_password
        )

        assert is_valid is True
        assert error is None


class TestPasswordRotation:
    """Test password rotation enforcement"""

    def test_rotation_required_old_password(self, password_policy):
        """Test that old passwords trigger rotation requirement"""
        last_changed = datetime.utcnow() - timedelta(days=95)
        rotation_required = password_policy.check_rotation_required(last_changed)

        assert rotation_required is True

    def test_rotation_not_required_recent_password(self, password_policy):
        """Test that recent passwords don't trigger rotation"""
        last_changed = datetime.utcnow() - timedelta(days=30)
        rotation_required = password_policy.check_rotation_required(last_changed)

        assert rotation_required is False

    def test_rotation_required_no_last_changed(self, password_policy):
        """Test that None last_changed triggers rotation"""
        rotation_required = password_policy.check_rotation_required(None)

        assert rotation_required is True

    def test_rotation_exactly_at_threshold(self, password_policy):
        """Test rotation at exact threshold (90 days)"""
        last_changed = datetime.utcnow() - timedelta(days=90)
        rotation_required = password_policy.check_rotation_required(last_changed)

        assert rotation_required is True


class TestCompleteValidation:
    """Test complete password validation flow"""

    @pytest.mark.asyncio
    async def test_valid_new_user_password(self, password_policy, db_session):
        """Test complete validation for new user"""
        password = "ValidNewP@ss123"

        # Should not raise exception
        await password_policy.validate_password_complete(
            password=password,
            session=db_session,
            user_id="new_user_complete",
            skip_history=True,  # New user
        )

    @pytest.mark.asyncio
    async def test_weak_password_raises_exception(self, password_policy, db_session):
        """Test that weak password raises PasswordPolicyViolation"""
        password = "weak"

        with pytest.raises(PasswordPolicyViolation) as exc_info:
            await password_policy.validate_password_complete(
                password=password,
                session=db_session,
                user_id="test_user_weak",
                skip_history=True,
            )

        assert len(exc_info.value.violations) > 0

    @pytest.mark.asyncio
    async def test_reused_password_raises_exception(self, password_policy, db_session):
        """Test that reused password raises PasswordPolicyViolation"""
        user_id = "test_user_reuse"
        password = "ReusedP@ssw0rd123"

        # Create user with password history
        user = User(
            id=user_id,
            username="testuser3",
            email="test3@example.com",
            hashed_password=password_policy.hash_password(password),
        )
        db_session.add(user)

        history_entry = PasswordHistory(
            user_id=user_id,
            password_hash=password_policy.hash_password(password),
        )
        db_session.add(history_entry)
        await db_session.commit()

        # Try to reuse same password
        with pytest.raises(PasswordPolicyViolation) as exc_info:
            await password_policy.validate_password_complete(
                password=password,
                session=db_session,
                user_id=user_id,
                skip_history=False,
            )

        assert any("Cannot reuse" in v for v in exc_info.value.violations)


class TestPasswordHashing:
    """Test password hashing functions"""

    def test_hash_password(self, password_policy):
        """Test password hashing"""
        password = "TestP@ssw0rd123"
        hashed = password_policy.hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self, password_policy):
        """Test password verification with correct password"""
        password = "TestP@ssw0rd123"
        hashed = password_policy.hash_password(password)

        is_valid = password_policy.verify_password(password, hashed)
        assert is_valid is True

    def test_verify_password_incorrect(self, password_policy):
        """Test password verification with incorrect password"""
        password = "TestP@ssw0rd123"
        wrong_password = "WrongP@ssw0rd123"
        hashed = password_policy.hash_password(password)

        is_valid = password_policy.verify_password(wrong_password, hashed)
        assert is_valid is False


def test_get_password_policy_singleton():
    """Test that get_password_policy returns global instance"""
    policy1 = get_password_policy()
    policy2 = get_password_policy()

    assert policy1 is policy2  # Same instance
    assert policy1.min_length == 12
    assert policy1.history_size == 5
    assert policy1.rotation_days == 90
