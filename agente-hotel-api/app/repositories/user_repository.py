from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.models.user import User


class UserRepository:
    """
    Repository for User model operations.
    Handles database interactions for user management.
    """

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(User).where(User.username == username))
            return result.scalars().first()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalars().first()

    async def create(self, user: User) -> User:
        """Create new user"""
        async with AsyncSessionFactory() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def update(self, user: User) -> User:
        """Update existing user"""
        async with AsyncSessionFactory() as session:
            # Merge is useful if the object is detached, but here we might need to be careful
            # If we have the object attached, we just commit.
            # Since we are using a new session for each method (anti-pattern for UoW but simple for now),
            # we should use merge or update.
            # For simplicity in this migration, we'll assume the user object passed might be detached.
            await session.merge(user)
            await session.commit()
            # Re-fetch to get latest state
            result = await session.execute(select(User).where(User.id == user.id))
            return result.scalars().first()

    async def update_login_stats(self, user_id: str, failed_attempts: int = 0, locked_until=None, last_login=None):
        """Update user login statistics"""
        async with AsyncSessionFactory() as session:
            values = {"failed_login_attempts": failed_attempts}
            if locked_until is not None:
                values["account_locked_until"] = locked_until
            if last_login is not None:
                values["last_login"] = last_login
            
            stmt = update(User).where(User.id == user_id).values(**values)
            await session.execute(stmt)
            await session.commit()
