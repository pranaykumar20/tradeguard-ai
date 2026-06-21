"""Admin API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_admin_list_users_demo_mode(client):
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data


@pytest.mark.asyncio
async def test_admin_permissions_catalog(client):
    resp = await client.get("/api/admin/permissions")
    assert resp.status_code == 200
    data = resp.json()
    assert "dashboard:view" in data["permissions"]
    assert any(r["id"] == "viewer" for r in data["roles"])


@pytest.mark.asyncio
async def test_demo_user_rbac_via_header(client):
    headers = {"X-Demo-User-Email": "viewer@test.com"}
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    user = me.json()["user"]
    assert user["email"] == "viewer@test.com"
    assert "admin:manage" not in user["permissions"]

    admin_resp = await client.get("/api/admin/users", headers=headers)
    assert admin_resp.status_code == 403
