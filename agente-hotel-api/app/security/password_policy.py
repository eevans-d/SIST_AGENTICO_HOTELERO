"""
Password Policy Enforcement Module
===================================

Implements enterprise-grade password policies:
- Minimum 12 characters
- Requires: uppercase, lowercase, digit, special character
- Password history (prevents reuse of last 5 passwords)
- Forced rotation every 90 days
- Configurable via settings

Author: Backend AI Team
Date: 2025-11-03
"""

import re
from datetime import datetime, timezone
from typing import List, Optional

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordPolicyViolation(Exception):
    """Raised when password doesn't meet policy requirements"""

    def __init__(self, message: str, violations: List[str]):
        super().__init__(message)
        self.violations = violations


class PasswordPolicy:
    """
    Enforces password policies for user authentication.

    Configuration:
        MIN_LENGTH: Minimum password length (default: 12)
        REQUIRE_UPPERCASE: Require at least one uppercase letter
        REQUIRE_LOWERCASE: Require at least one lowercase letter
        REQUIRE_DIGIT: Require at least one digit
        REQUIRE_SPECIAL: Require at least one special character
        HISTORY_SIZE: Number of previous passwords to check (default: 5)
        ROTATION_DAYS: Days before forced rotation (default: 90)
    """

    def __init__(
        self,
        min_length: int = 12,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        history_size: int = 5,
        rotation_days: int = 90,
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.history_size = history_size
        self.rotation_days = rotation_days

        # Special characters allowed
        self.special_chars = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?"

    def validate_password_strength(self, password: str) -> tuple[bool, List[str]]:
        """
        Validate password meets strength requirements.

        Args:
            password: Plain text password to validate

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []

        # Length check
        if len(password) < self.min_length:
            violations.append(f"Password must be at least {self.min_length} characters long")

        # Uppercase check
        if self.require_uppercase and not re.search(r"[A-Z]", password):
            violations.append("Password must contain at least one uppercase letter")

        # Lowercase check
        if self.require_lowercase and not re.search(r"[a-z]", password):
            violations.append("Password must contain at least one lowercase letter")

        # Digit check
        if self.require_digit and not re.search(r"\d", password):
            violations.append("Password must contain at least one digit")

        # Special character check
        if self.require_special and not re.search(rf"[{re.escape(self.special_chars)}]", password):
            violations.append(
                f"Password must contain at least one special character from: {self.special_chars}"
            )

        is_valid = len(violations) == 0
        return is_valid, violations

    async def validate_password_history(
        self,
        session: AsyncSession,
        user_id: str,
        new_password: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if password was used in recent history.

        Args:
            session: Database session
            user_id: User identifier
            new_password: Plain text password to check

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Import here to avoid circular dependency
            from app.models.user import PasswordHistory

            # Get last N password hashes for user
            stmt = (
                select(PasswordHistory.password_hash)
                .where(PasswordHistory.user_id == user_id)
                .order_by(PasswordHistory.created_at.desc())
                .limit(self.history_size)
            )

            result = await session.execute(stmt)
            password_hashes = result.scalars().all()

            # Check if new password matches any in history
            for old_hash in password_hashes:
                if pwd_context.verify(new_password, old_hash):
                    logger.warning(
                        "password_reuse_attempt",
                        user_id=user_id,
                        history_size=len(password_hashes),
                    )
                    return False, f"Password was used recently. Cannot reuse last {self.history_size} passwords"

            return True, None

        except Exception as e:
            logger.error(
                "password_history_check_failed",
                user_id=user_id,
                error=str(e),
            )
            # Fail open - don't block user if history check fails
            return True, None

    def check_rotation_required(self, last_changed: Optional[datetime]) -> bool:
        """
        Check if password rotation is required based on age.

        Args:
            last_changed: Datetime when password was last changed

        Returns:
            True if rotation required, False otherwise
        """
        if not last_changed:
            # No last changed date means never changed - require rotation
            return True

        # Ensure timezone-aware arithmetic (assume UTC if naive)
        now = datetime.now(timezone.utc)
        if last_changed.tzinfo is None:
            last_changed = last_changed.replace(tzinfo=timezone.utc)
        age = now - last_changed
        rotation_required = age.days >= self.rotation_days

        if rotation_required:
            logger.info(
                "password_rotation_required",
                age_days=age.days,
                threshold_days=self.rotation_days,
            )

        return rotation_required

    async def validate_password_complete(
        self,
        password: str,
        session: AsyncSession,
        user_id: str,
        last_changed: Optional[datetime] = None,
        skip_history: bool = False,
    ) -> None:
        """
        Complete password validation including strength, history, and rotation.

        Args:
            password: Plain text password to validate
            session: Database session
            user_id: User identifier
            last_changed: When password was last changed
            skip_history: Skip history check (for new users)

        Raises:
            PasswordPolicyViolation: If password doesn't meet policy
        """
        violations = []

        # 1. Strength validation
        is_strong, strength_violations = self.validate_password_strength(password)
        if not is_strong:
            violations.extend(strength_violations)

        # 2. History validation (unless skipped for new users)
        if not skip_history:
            history_valid, history_error = await self.validate_password_history(
                session, user_id, password
            )
            if not history_valid and history_error:
                violations.append(history_error)

        # 3. Rotation check (informational - doesn't block)
        if last_changed:
            rotation_required = self.check_rotation_required(last_changed)
            if rotation_required:
                logger.warning(
                    "password_rotation_overdue",
                    user_id=user_id,
                    days_overdue=(
                        (datetime.now(timezone.utc) - (last_changed.replace(tzinfo=timezone.utc) if last_changed.tzinfo is None else last_changed)).days
                        - self.rotation_days
                    ),
                )

        # Raise if any violations
        if violations:
            logger.warning(
                "password_policy_violation",
                user_id=user_id,
                violations=violations,
            )
            raise PasswordPolicyViolation(
                message="Password does not meet policy requirements",
                violations=violations,
            )

        logger.info("password_policy_validated", user_id=user_id)

    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to compare

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)


# Global password policy instance (configurable via settings)
password_policy = PasswordPolicy(
    min_length=12,
    require_uppercase=True,
    require_lowercase=True,
    require_digit=True,
    require_special=True,
    history_size=5,
    rotation_days=90,
)


def get_password_policy() -> PasswordPolicy:
    """Dependency injection for password policy"""
    return password_policy
