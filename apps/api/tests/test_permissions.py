"""RBAC permission helpers."""

from app.core.permissions import (
    effective_permissions,
    has_permission,
    resolve_initial_role,
)


def test_platform_admin_gets_all_permissions():
    perms = effective_permissions("platform_admin", None)
    assert "admin:manage" in perms
    assert "dashboard:view" in perms
    assert len(perms) >= 10


def test_viewer_limited_permissions():
    perms = effective_permissions("viewer", None)
    assert "dashboard:view" in perms
    assert "portfolio:view" in perms
    assert "admin:manage" not in perms
    assert "chat:use" not in perms


def test_custom_permissions_override():
    perms = effective_permissions("viewer", ["chat:use", "analysis:use"])
    assert "chat:use" in perms
    assert "analysis:use" in perms
    assert "admin:manage" not in perms


def test_has_permission_helper():
    assert has_permission("trader", None, "chat:use") is True
    assert has_permission("viewer", None, "admin:manage") is False


def test_resolve_initial_role_from_admin_emails():
    assert resolve_initial_role("Admin@Example.com", {"admin@example.com"}) == "platform_admin"
    assert resolve_initial_role("user@example.com", {"admin@example.com"}) == "user"
