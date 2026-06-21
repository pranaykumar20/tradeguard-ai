"""Role-based access control — permissions, role templates, and helpers."""

from __future__ import annotations

from typing import Literal

UserRole = Literal["platform_admin", "trader", "analyst", "viewer", "user"]

# All granular permissions in the app.
PERMISSION_DASHBOARD = "dashboard:view"
PERMISSION_PORTFOLIO = "portfolio:view"
PERMISSION_CHAT = "chat:use"
PERMISSION_MONITORING = "monitoring:view"
PERMISSION_ANALYSIS = "analysis:use"
PERMISSION_JOURNAL = "journal:view"
PERMISSION_APPROVALS = "approvals:manage"
PERMISSION_ONBOARDING = "onboarding:use"
PERMISSION_STRATEGIES = "strategies:use"
PERMISSION_OBSERVABILITY = "observability:view"
PERMISSION_AUTOMATION = "automation:use"
PERMISSION_VALIDATION = "validation:view"
PERMISSION_ADMIN = "admin:manage"

ALL_PERMISSIONS: tuple[str, ...] = (
    PERMISSION_DASHBOARD,
    PERMISSION_PORTFOLIO,
    PERMISSION_CHAT,
    PERMISSION_MONITORING,
    PERMISSION_ANALYSIS,
    PERMISSION_JOURNAL,
    PERMISSION_APPROVALS,
    PERMISSION_ONBOARDING,
    PERMISSION_STRATEGIES,
    PERMISSION_OBSERVABILITY,
    PERMISSION_AUTOMATION,
    PERMISSION_VALIDATION,
    PERMISSION_ADMIN,
)

DEFAULT_USER_PERMISSIONS: tuple[str, ...] = (
    PERMISSION_DASHBOARD,
    PERMISSION_PORTFOLIO,
    PERMISSION_CHAT,
    PERMISSION_MONITORING,
    PERMISSION_ANALYSIS,
    PERMISSION_JOURNAL,
    PERMISSION_APPROVALS,
    PERMISSION_ONBOARDING,
    PERMISSION_VALIDATION,
)

ROLE_TEMPLATES: dict[str, tuple[str, ...]] = {
    "platform_admin": ALL_PERMISSIONS,
    "trader": (
        PERMISSION_DASHBOARD,
        PERMISSION_PORTFOLIO,
        PERMISSION_CHAT,
        PERMISSION_MONITORING,
        PERMISSION_ANALYSIS,
        PERMISSION_APPROVALS,
        PERMISSION_ONBOARDING,
        PERMISSION_JOURNAL,
    ),
    "analyst": (
        PERMISSION_DASHBOARD,
        PERMISSION_PORTFOLIO,
        PERMISSION_CHAT,
        PERMISSION_ANALYSIS,
        PERMISSION_JOURNAL,
        PERMISSION_OBSERVABILITY,
        PERMISSION_VALIDATION,
    ),
    "viewer": (
        PERMISSION_DASHBOARD,
        PERMISSION_PORTFOLIO,
        PERMISSION_MONITORING,
    ),
    "user": DEFAULT_USER_PERMISSIONS,
}

ROLE_LABELS: dict[str, str] = {
    "platform_admin": "Platform Admin",
    "trader": "Trader",
    "analyst": "Analyst",
    "viewer": "Viewer",
    "user": "Standard User",
}


def normalize_role(role: str | None) -> str:
    value = (role or "user").strip().lower()
    if value in ROLE_TEMPLATES:
        return value
    return "user"


def effective_permissions(role: str | None, custom: list[str] | None = None) -> list[str]:
    """Resolve final permission list from role + optional custom overrides."""
    normalized = normalize_role(role)
    if normalized == "platform_admin":
        return list(ALL_PERMISSIONS)
    if custom:
        return sorted({p for p in custom if p in ALL_PERMISSIONS})
    return list(ROLE_TEMPLATES.get(normalized, DEFAULT_USER_PERMISSIONS))


def has_permission(role: str | None, custom: list[str] | None, permission: str) -> bool:
    return permission in effective_permissions(role, custom)


def is_platform_admin(role: str | None) -> bool:
    return normalize_role(role) == "platform_admin"


def resolve_initial_role(email: str, admin_emails: set[str]) -> str:
    if email.strip().lower() in admin_emails:
        return "platform_admin"
    return "user"
