from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import HTTPException, status

from app.core.rbac import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.models.auth import Token, UserPublic
from app.repositories.data_store import DataStore
from app.services.analytics_service import EventLogger


class AuthService:
    def __init__(self, store: DataStore, event_logger: EventLogger) -> None:
        self.store = store
        self.event_logger = event_logger
        self._seed_users()

    def _seed_users(self) -> None:
        seed = [
            {
                "user_id": "u-hr-001",
                "username": "hr_admin",
                "full_name": "Avery Jordan",
                "role": Role.HR,
                "manager_id": None,
                "team_members": ["u-mgr-001", "u-emp-001", "u-emp-002"],
                "password": "hr123",
                "gdpr_consent": True,
            },
            {
                "user_id": "u-mgr-001",
                "username": "mgr_jane",
                "full_name": "Jane Rivera",
                "role": Role.MANAGER,
                "manager_id": "u-hr-001",
                "team_members": ["u-emp-001", "u-emp-002"],
                "password": "manager123",
                "gdpr_consent": True,
            },
            {
                "user_id": "u-emp-001",
                "username": "emp_alex",
                "full_name": "Alex Kim",
                "role": Role.EMPLOYEE,
                "manager_id": "u-mgr-001",
                "team_members": [],
                "password": "employee123",
                "gdpr_consent": True,
            },
            {
                "user_id": "u-emp-002",
                "username": "emp_sam",
                "full_name": "Sam Patel",
                "role": Role.EMPLOYEE,
                "manager_id": "u-mgr-001",
                "team_members": [],
                "password": "employee456",
                "gdpr_consent": True,
            },
        ]

        with self.store.lock:
            if self.store.users:
                return
            for user in seed:
                record = {
                    **user,
                    "hashed_password": hash_password(user["password"]),
                }
                del record["password"]
                self.store.users[record["user_id"]] = record

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        with self.store.lock:
            users = list(self.store.users.values())
        user = next((u for u in users if u["username"] == username), None)
        if not user:
            return None
        if not verify_password(password, user["hashed_password"]):
            return None
        return user

    def issue_token(self, user: dict[str, Any]) -> Token:
        token, expires_at = create_access_token(
            subject=user["user_id"],
            role=user["role"],
            expires_delta=timedelta(minutes=120),
        )
        self.event_logger.log_event(
            event_type="auth_login",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={"username": user["username"]},
        )
        return Token(access_token=token, expires_at=expires_at)

    def require_user(self, user_id: str) -> dict[str, Any]:
        with self.store.lock:
            user = self.store.users.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return user

    def as_public(self, user: dict[str, Any]) -> UserPublic:
        return UserPublic(
            user_id=user["user_id"],
            username=user["username"],
            full_name=user["full_name"],
            role=user["role"],
            manager_id=user.get("manager_id"),
            team_members=user.get("team_members", []),
            gdpr_consent=bool(user.get("gdpr_consent", True)),
        )

    def list_users(self) -> list[UserPublic]:
        with self.store.lock:
            users = list(self.store.users.values())
        return [self.as_public(u) for u in users]

    def is_manager_of(self, manager_id: str, employee_id: str) -> bool:
        with self.store.lock:
            manager = self.store.users.get(manager_id)
        if not manager:
            return False
        return employee_id in manager.get("team_members", [])

    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self.store.lock:
            if user_id not in self.store.users:
                raise HTTPException(status_code=404, detail="User not found")
            self.store.users[user_id].update(updates)
            return self.store.users[user_id]
