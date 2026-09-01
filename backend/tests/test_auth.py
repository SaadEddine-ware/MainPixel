import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.v1.auth import _login_attempts

transport = ASGITransport(app=app)
BASE = "/api/v1"


def _clear_rate_limit():
    _login_attempts.clear()


@pytest.mark.asyncio
async def test_unauthenticated_returns_401():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(f"{BASE}/classes/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 401
    assert "Not authenticated" in r.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_token_returns_401():
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            f"{BASE}/classes/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_success():
    _clear_rate_limit()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            f"{BASE}/auth/login",
            data={"username": "super@mainpixel.ma", "password": "SuperAdmin123!"},
        )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["role"] == "super_admin"


@pytest.mark.asyncio
async def test_login_wrong_password():
    _clear_rate_limit()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            f"{BASE}/auth/login",
            data={"username": "super@mainpixel.ma", "password": "wrongpassword123"},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_access():
    _clear_rate_limit()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            f"{BASE}/auth/login",
            data={"username": "super@mainpixel.ma", "password": "SuperAdmin123!"},
        )
        token = login.json()["access_token"]
        r = await client.get(
            f"{BASE}/classes/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code in [200, 404]
    assert r.status_code != 401


@pytest.mark.asyncio
async def test_rate_limiting():
    _clear_rate_limit()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(5):
            await client.post(
                f"{BASE}/auth/login",
                data={"username": f"ratelimittest{i}@fake.com", "password": "wrong"},
            )
        r = await client.post(
            f"{BASE}/auth/login",
            data={"username": "ratelimittest99@fake.com", "password": "wrong"},
        )
    assert r.status_code == 429
    assert "Too many" in r.json()["detail"]
    _clear_rate_limit()
