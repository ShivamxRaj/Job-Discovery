from fastapi import APIRouter, Depends, HTTPException, status, Header, BackgroundTasks
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta, datetime, timezone
import uuid
from jose import jwt, JWTError

from app.db.session import get_db
from app.schemas.schemas import (
    UserCreate, UserResponse, UserLogin, Token, GoogleLogin,
    UserPreferencesUpdate, UserPreferencesResponse, TokenRefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, EmailVerifyRequest, LogoutRequest
)
from app.repositories.user import user_repo
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, get_current_user, hash_token
from app.models.models import User, UserPreferences, AuditLog
from app.core.config import settings
from app.core.redis import redis_service
from app.utils.email import send_verification_email, send_reset_password_email

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    existing_user = await user_repo.get_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    hashed_pwd = get_password_hash(user_in.password)
    user_dict = {
        "email": user_in.email,
        "hashed_password": hashed_pwd,
        "is_active": True,
        "is_superuser": False
    }
    user = await user_repo.create(db, obj_in=user_dict)
    
    # Initialize blank preferences for user
    await user_repo.update_preferences(db, user.id, {
        "preferred_locations": [],
        "preferred_job_types": [],
        "preferred_roles": [],
        "min_salary": None,
        "is_remote": False
    })
    
    await db.commit()
    return user

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate and return access and refresh tokens"""
    user = await user_repo.get_by_email(db, user_in.email)
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    # Store in database as jti:hashed_token
    decoded = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti = decoded.get("jti")
    hashed = hash_token(refresh_token)
    stored_val = f"{jti}:{hashed}"
    
    # Update refresh token in Auth DB record
    # Find local auth or create
    local_auth = next((a for a in user.auth_accounts if a.provider == "local"), None)
    if not local_auth:
        local_auth = await user_repo.create_oauth_account(db, user_id=user.id, provider="local", provider_id=str(user.id))
        user.auth_accounts.append(local_auth)
    local_auth.refresh_token = stored_val
    
    await db.commit()
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/google", response_model=Token)
async def google_oauth(payload: GoogleLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate a Google OAuth ID token using google-auth library"""
    if settings.GOOGLE_CLIENT_ID and not payload.credential.startswith("mock_"):
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            
            id_info = id_token.verify_oauth2_token(
                payload.credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google token verification failed: {str(e)}"
            )
    else:
        # Development / Testing fallback
        if payload.credential == "error":
            raise HTTPException(status_code=400, detail="Invalid Google credentials")
            
        mock_email = "oauth.user@gmail.com"
        if payload.credential.startswith("mock_email:"):
            mock_email = payload.credential.split("mock_email:")[1]
            
        id_info = {
            "email": mock_email,
            "sub": f"google-oauth-sub-{abs(hash(mock_email))}"
        }
        
    email = id_info["email"]
    provider_id = id_info["sub"]
    
    user = await user_repo.get_by_email(db, email)
    if not user:
        # Create user
        user = await user_repo.create(db, obj_in={
            "email": email,
            "is_active": True,
            "is_superuser": False
        })
        # Create auth reference
        await user_repo.create_oauth_account(db, user_id=user.id, provider="google", provider_id=provider_id)
        # Create empty preferences
        await user_repo.update_preferences(db, user.id, {"is_remote": False})
    
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    # Store refresh token in Auth DB record
    google_auth = next((a for a in user.auth_accounts if a.provider == "google"), None)
    if not google_auth:
        google_auth = await user_repo.create_oauth_account(db, user_id=user.id, provider="google", provider_id=provider_id)
        user.auth_accounts.append(google_auth)
        
    decoded = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti = decoded.get("jti")
    hashed = hash_token(refresh_token)
    google_auth.refresh_token = f"{jti}:{hashed}"
    
    await db.commit()
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """Fetch current user profile"""
    return current_user

@router.get("/preferences", response_model=UserPreferencesResponse)
async def read_preferences(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Fetch user preferences"""
    prefs = await user_repo.get_preferences(db, current_user.id)
    if not prefs:
        prefs = await user_repo.update_preferences(db, current_user.id, {"is_remote": False})
        await db.commit()
    return prefs

@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    prefs_in: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user preferences"""
    prefs = await user_repo.update_preferences(db, current_user.id, prefs_in.model_dump(exclude_unset=True))
    await db.commit()
    return prefs

@router.post("/refresh", response_model=Token)
async def refresh(payload: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access and refresh tokens. Implements token rotation and reuse detection."""
    try:
        decoded = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = decoded.get("type")
        if token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        
        jti = decoded.get("jti")
        user_id = decoded.get("sub")
        if not jti or not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
            
        # Check if refresh token is blacklisted/revoked (Reuse Detection)
        if await redis_service.is_blacklisted(jti):
            user = await user_repo.get(db, id=int(user_id))
            if user:
                for auth in user.auth_accounts:
                    if auth.refresh_token:
                        try:
                            parts = auth.refresh_token.split(":")
                            if len(parts) == 2:
                                ref_jti = parts[0]
                                await redis_service.blacklist_token(ref_jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
                        except Exception:
                            pass
                        auth.refresh_token = None
                await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

        user = await user_repo.get(db, id=int(user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        # Verify incoming refresh token matches stored hashed token
        local_auth = next((a for a in user.auth_accounts if a.provider == "local"), None)
        if not local_auth or not local_auth.refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
        
        parts = local_auth.refresh_token.split(":")
        if len(parts) != 2 or parts[1] != hash_token(payload.refresh_token):
            # Token was rotated or doesn't match current active session
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        # Rotate the refresh token
        exp_time = decoded.get("exp")
        now_ts = datetime.now(timezone.utc).timestamp()
        remaining_ttl = int(max(0, exp_time - now_ts)) if exp_time else settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        await redis_service.blacklist_token(jti, remaining_ttl)

        new_access = create_access_token(user.id)
        new_refresh = create_refresh_token(user.id)

        new_decoded = jwt.decode(new_refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        new_jti = new_decoded.get("jti")
        new_hashed = hash_token(new_refresh)
        new_stored_val = f"{new_jti}:{new_hashed}"

        if not local_auth:
            local_auth = await user_repo.create_oauth_account(db, user_id=user.id, provider="local", provider_id=str(user.id))
            user.auth_accounts.append(local_auth)
        local_auth.refresh_token = new_stored_val
        
        await db.commit()
        return Token(access_token=new_access, refresh_token=new_refresh)

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

@router.post("/logout")
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    """Log out user, blacklisting both access and refresh tokens."""
    if authorization and authorization.startswith("Bearer "):
        access_token = authorization.split(" ")[1]
        try:
            acc_dec = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            acc_jti = acc_dec.get("jti")
            acc_exp = acc_dec.get("exp")
            if acc_jti:
                now_ts = datetime.now(timezone.utc).timestamp()
                remaining_ttl = int(max(0, acc_exp - now_ts)) if acc_exp else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
                await redis_service.blacklist_token(acc_jti, remaining_ttl)
        except Exception:
            pass

    try:
        ref_dec = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        ref_jti = ref_dec.get("jti")
        ref_exp = ref_dec.get("exp")
        if ref_jti:
            now_ts = datetime.now(timezone.utc).timestamp()
            remaining_ttl = int(max(0, ref_exp - now_ts)) if ref_exp else settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
            await redis_service.blacklist_token(ref_jti, remaining_ttl)
    except Exception:
        pass

    for auth in current_user.auth_accounts:
        if auth.refresh_token:
            parts = auth.refresh_token.split(":")
            if len(parts) == 2 and (parts[1] == hash_token(payload.refresh_token) or auth.provider == "local"):
                auth.refresh_token = None
        elif auth.provider == "local":
            auth.refresh_token = None
    
    await db.commit()
    return {"message": "Successfully logged out"}

@router.post("/request-verification")
async def request_verification(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate and save email verification token."""
    if current_user.is_verified:
        return {"message": "Email is already verified"}

    token = str(uuid.uuid4())
    await redis_service.set_token_data(f"verify_email:{token}", str(current_user.id), 86400)
    print(f"EMAIL VERIFICATION LINK: http://localhost:3000/verify-email?token={token}")
    
    # Store only audit metadata in PostgreSQL
    audit = AuditLog(
        user_id=current_user.id,
        action="email_verification_requested",
        details={"email": current_user.email}
    )
    db.add(audit)
    await db.commit()
    
    background_tasks.add_task(send_verification_email, current_user.email, token)
    
    return {
        "message": "Verification email generated successfully",
        "token": token
    }

@router.post("/verify-email")
async def verify_email(payload: EmailVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify user email using verification token."""
    key = f"verify_email:{payload.token}"
    user_id_str = await redis_service.get_token_data(key)
    if not user_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user = await user_repo.get(db, id=int(user_id_str))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    
    # Store only audit metadata in PostgreSQL
    audit = AuditLog(
        user_id=user.id,
        action="email_verified",
        details={"email": user.email}
    )
    db.add(audit)
    
    await redis_service.delete_token_data(key)
    await db.commit()
    return {"message": "Email successfully verified"}

@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Generate password reset token if email exists."""
    user = await user_repo.get_by_email(db, payload.email)
    if not user:
        return {"message": "Password reset email generated successfully if user exists"}

    token = str(uuid.uuid4())
    await redis_service.set_token_data(f"reset_password:{token}", str(user.id), 3600)
    print(f"PASSWORD RESET LINK: http://localhost:3000/reset-password?token={token}")

    # Store only audit metadata in PostgreSQL
    audit = AuditLog(
        user_id=user.id,
        action="password_reset_requested",
        details={"email": user.email}
    )
    db.add(audit)
    await db.commit()

    background_tasks.add_task(send_reset_password_email, user.email, token)

    return {
        "message": "Password reset email generated successfully if user exists",
        "token": token
    }

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset user password using token."""
    key = f"reset_password:{payload.token}"
    user_id_str = await redis_service.get_token_data(key)
    if not user_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = await user_repo.get(db, id=int(user_id_str))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(payload.new_password)
    
    # Revoke all current refresh tokens for this user
    for auth in user.auth_accounts:
        if auth.refresh_token:
            try:
                parts = auth.refresh_token.split(":")
                if len(parts) == 2:
                    ref_jti = parts[0]
                    await redis_service.blacklist_token(ref_jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
            except Exception:
                pass
            auth.refresh_token = None

    # Store only audit metadata in PostgreSQL
    audit = AuditLog(
        user_id=user.id,
        action="password_reset",
        details={"email": user.email}
    )
    db.add(audit)

    await redis_service.delete_token_data(key)
    await db.commit()
    return {"message": "Password reset successfully"}
