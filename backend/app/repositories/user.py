from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.models import User, Auth, UserPreferences

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get(self, db: AsyncSession, id: Any) -> Optional[User]:
        from sqlalchemy.orm import selectinload
        query = select(User).where(User.id == id).options(selectinload(User.auth_accounts))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        from sqlalchemy.orm import selectinload
        query = select(User).where(User.email == email).options(selectinload(User.auth_accounts))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_oauth_account(
        self, db: AsyncSession, *, user_id: int, provider: str, provider_id: str
    ) -> Auth:
        auth_obj = Auth(user_id=user_id, provider=provider, provider_id=provider_id)
        db.add(auth_obj)
        await db.flush()
        return auth_obj

    async def get_oauth_account(
        self, db: AsyncSession, *, provider: str, provider_id: str
    ) -> Optional[Auth]:
        query = select(Auth).where(Auth.provider == provider, Auth.provider_id == provider_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_preferences(self, db: AsyncSession, user_id: int) -> Optional[UserPreferences]:
        query = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_preferences(
        self, db: AsyncSession, user_id: int, prefs: dict
    ) -> UserPreferences:
        existing = await self.get_preferences(db, user_id)
        if existing:
            for k, v in prefs.items():
                setattr(existing, k, v)
            db.add(existing)
        else:
            existing = UserPreferences(user_id=user_id, **prefs)
            db.add(existing)
        await db.flush()
        return existing

user_repo = UserRepository()
