from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any


class DataStore:
    """Simple in-memory repository for demo-scale workflow state."""

    def __init__(self) -> None:
        self.lock = RLock()
        self.users: dict[str, dict[str, Any]] = {}
        self.leave_requests: dict[str, dict[str, Any]] = {}
        self.document_requests: dict[str, dict[str, Any]] = {}
        self.onboarding_tasks: dict[str, dict[str, Any]] = {}
        self.policy_responses: dict[str, dict[str, Any]] = {}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
