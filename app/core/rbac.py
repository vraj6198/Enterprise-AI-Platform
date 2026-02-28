from enum import Enum


class Role(str, Enum):
    HR = "HR"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.HR: {
        "policy:read",
        "workflow:leave:create",
        "workflow:leave:approve:any",
        "workflow:document:request",
        "workflow:document:fulfill",
        "workflow:onboarding:trigger",
        "governance:manage",
        "analytics:view",
        "users:read",
    },
    Role.MANAGER: {
        "policy:read",
        "workflow:leave:create",
        "workflow:leave:approve:team",
        "workflow:document:request",
        "workflow:onboarding:view",
        "analytics:view",
    },
    Role.EMPLOYEE: {
        "policy:read",
        "workflow:leave:create",
        "workflow:document:request",
    },
}


def has_permission(role: Role, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
