import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.v1.auth import _login_attempts

transport = ASGITransport(app=app)
BASE = "/api/v1"


def _clear_rate_limit():
    _login_attempts.clear()


@pytest.mark.asyncio
async def test_refresh_token_works():
    _clear_rate_limit()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            f"{BASE}/auth/login",
            data={"username": "super@mainpixel.ma", "password": "SuperAdmin123!"},
        )
        refresh_token = r.json()["refresh_token"]
        r2 = await client.post(
            f"{BASE}/auth/refresh",
            params={"refresh_token": refresh_token},
        )
    assert r2.status_code == 200
    assert "access_token" in r2.json()


@pytest.mark.asyncio
async def test_invalid_refresh_token():
    _clear_rate_limit()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            f"{BASE}/auth/refresh",
            params={"refresh_token": "invalid.token.here"},
        )
    assert r.status_code == 401
