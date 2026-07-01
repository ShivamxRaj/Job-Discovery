# pyrefly: ignore [missing-import]
import pytest
from app.repositories.user import user_repo
from app.core.security import get_password_hash, verify_password

@pytest.mark.asyncio
async def test_user_password_hashing():
    password = "supersecretpassword"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

@pytest.mark.asyncio
async def test_create_user(db_session):
    email = "test@example.com"
    pwd_hash = get_password_hash("password123")
    
    user = await user_repo.create(db_session, obj_in={
        "email": email,
        "hashed_password": pwd_hash,
        "is_active": True
    })
    await db_session.commit()
    
    assert user.id is not None
    assert user.email == email
    
    fetched = await user_repo.get_by_email(db_session, email)
    assert fetched is not None
    assert fetched.id == user.id
