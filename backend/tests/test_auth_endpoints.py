import pytest
from app.core.security import verify_password, get_password_hash
from app.repositories.user import user_repo

@pytest.mark.asyncio
async def test_auth_registration_and_login_flow(client):
    # 1. Register a new user
    register_payload = {
        "email": "user@example.com",
        "password": "strongpassword123"
    }
    res = await client.post("/api/v1/auth/register", json=register_payload)
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["email"] == "user@example.com"
    assert user_data["is_active"] is True
    assert user_data["is_verified"] is False

    # 2. Duplicate registration should fail
    res_dup = await client.post("/api/v1/auth/register", json=register_payload)
    assert res_dup.status_code == 400

    # 3. Login with incorrect password should fail
    login_payload_fail = {
        "email": "user@example.com",
        "password": "wrongpassword"
    }
    res_login_fail = await client.post("/api/v1/auth/login", json=login_payload_fail)
    assert res_login_fail.status_code == 401

    # 4. Login with correct password should succeed and return tokens
    login_payload = {
        "email": "user@example.com",
        "password": "strongpassword123"
    }
    res_login = await client.post("/api/v1/auth/login", json=login_payload)
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 5. Access protected route /me with access token
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    res_me = await client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_reuse_detection(client):
    # Setup: Register and Login
    register_payload = {
        "email": "refresh@example.com",
        "password": "password123"
    }
    await client.post("/api/v1/auth/register", json=register_payload)
    res_login = await client.post("/api/v1/auth/login", json=register_payload)
    token_data = res_login.json()
    refresh_token = token_data["refresh_token"]

    # 1. First refresh should succeed and rotate tokens
    res_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res_refresh.status_code == 200
    new_tokens = res_refresh.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != refresh_token

    # 2. Reuse of old refresh token should be blocked (Reuse Detection)
    res_reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res_reuse.status_code == 401


@pytest.mark.asyncio
async def test_email_verification_flow(client):
    # Setup: Register and Login
    email = "verify_test@example.com"
    register_payload = {
        "email": email,
        "password": "password123"
    }
    await client.post("/api/v1/auth/register", json=register_payload)
    res_login = await client.post("/api/v1/auth/login", json=register_payload)
    token_data = res_login.json()
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    # 1. Request verification token
    res_req = await client.post("/api/v1/auth/request-verification", headers=headers)
    assert res_req.status_code == 200
    token = res_req.json()["token"]
    assert token is not None

    # 2. Verify email using the token
    res_verify = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert res_verify.status_code == 200

    # 3. Check is_verified is True
    res_me = await client.get("/api/v1/auth/me", headers=headers)
    assert res_me.json()["is_verified"] is True


@pytest.mark.asyncio
async def test_password_reset_flow(client):
    # Setup: Register
    email = "reset_test@example.com"
    register_payload = {
        "email": email,
        "password": "oldpassword123"
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    # 1. Request password reset
    res_forgot = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert res_forgot.status_code == 200
    token = res_forgot.json()["token"]
    assert token is not None

    # 2. Reset password
    res_reset = await client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": "newpassword123"
    })
    assert res_reset.status_code == 200

    # 3. Old password login should fail
    res_login_old = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "oldpassword123"
    })
    assert res_login_old.status_code == 401

    # 4. New password login should succeed
    res_login_new = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "newpassword123"
    })
    assert res_login_new.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_tokens(client):
    # Setup: Register and Login
    register_payload = {
        "email": "logout@example.com",
        "password": "password123"
    }
    await client.post("/api/v1/auth/register", json=register_payload)
    res_login = await client.post("/api/v1/auth/login", json=register_payload)
    token_data = res_login.json()
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}

    # 1. Logout
    res_logout = await client.post("/api/v1/auth/logout", json={"refresh_token": token_data["refresh_token"]}, headers=headers)
    assert res_logout.status_code == 200

    # 2. Accessing protected route should now fail
    res_me = await client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 401

    # 3. Refreshing token should now fail
    res_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": token_data["refresh_token"]})
    assert res_refresh.status_code == 401
