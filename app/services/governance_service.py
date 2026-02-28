from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.core.rbac import Role
from app.models.governance import ErasureResponse, RetentionCleanupResponse, SubjectAccessResponse
from app.repositories.data_store import DataStore
from app.services.analytics_service import EventLogger


class GovernanceService:
    def __init__(self, store: DataStore, event_logger: EventLogger) -> None:
        self.store = store
        self.event_logger = event_logger

    def ensure_consent(self, user: dict[str, Any], purpose: str) -> None:
        if not bool(user.get("gdpr_consent", False)):
            raise HTTPException(
                status_code=403,
                detail=f"GDPR consent missing for purpose '{purpose}'.",
            )

    def update_consent(
        self,
        actor: dict[str, Any],
        target_user_id: str,
        gdpr_consent: bool,
    ) -> dict[str, Any]:
        if actor["role"] != Role.HR and actor["user_id"] != target_user_id:
            raise HTTPException(status_code=403, detail="Not allowed to change this consent setting")

        with self.store.lock:
            target = self.store.users.get(target_user_id)
            if not target:
                raise HTTPException(status_code=404, detail="Target user not found")
            target["gdpr_consent"] = gdpr_consent

        self.event_logger.log_event(
            event_type="governance_event",
            actor_id=actor["user_id"],
            actor_role=actor["role"],
            details={
                "action": "consent_update",
                "target_user_id": target_user_id,
                "gdpr_consent": gdpr_consent,
            },
        )

        return target

    def subject_access_request(
        self,
        actor: dict[str, Any],
        target_user_id: str,
    ) -> SubjectAccessResponse:
        if actor["role"] != Role.HR and actor["user_id"] != target_user_id:
            raise HTTPException(status_code=403, detail="Not allowed to access this data")

        with self.store.lock:
            user = self.store.users.get(target_user_id)
            if not user:
                raise HTTPException(status_code=404, detail="Target user not found")

            user_profile = {
                "user_id": user["user_id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
                "manager_id": user.get("manager_id"),
                "team_members": user.get("team_members", []),
                "gdpr_consent": bool(user.get("gdpr_consent", True)),
            }

            leave_rows = [
                row for row in self.store.leave_requests.values() if row["employee_id"] == target_user_id
            ]
            document_rows = [
                row
                for row in self.store.document_requests.values()
                if row["employee_id"] == target_user_id
            ]
            task_rows = [
                row for row in self.store.onboarding_tasks.values() if row["employee_id"] == target_user_id
            ]

        self.event_logger.log_event(
            event_type="governance_event",
            actor_id=actor["user_id"],
            actor_role=actor["role"],
            details={
                "action": "subject_access_request",
                "target_user_id": target_user_id,
            },
        )

        return SubjectAccessResponse(
            user_profile=user_profile,
            leave_requests=leave_rows,
            document_requests=document_rows,
            onboarding_tasks=task_rows,
        )

    def erase_user_data(self, actor: dict[str, Any], target_user_id: str) -> ErasureResponse:
        if actor["role"] != Role.HR:
            raise HTTPException(status_code=403, detail="Only HR can perform data erasure")

        with self.store.lock:
            user = self.store.users.get(target_user_id)
            if not user:
                raise HTTPException(status_code=404, detail="Target user not found")

            anonymized_ref = f"anon-{hashlib.sha256(target_user_id.encode()).hexdigest()[:10]}"
            user["full_name"] = "Anonymized User"
            user["username"] = anonymized_ref
            user["gdpr_consent"] = False
            user["team_members"] = []

            records_updated = 0

            for row in self.store.leave_requests.values():
                if row["employee_id"] == target_user_id:
                    row["employee_id"] = anonymized_ref
                    row["reason"] = "[REDACTED]"
                    records_updated += 1

            for row in self.store.document_requests.values():
                if row["employee_id"] == target_user_id:
                    row["employee_id"] = anonymized_ref
                    row["purpose"] = "[REDACTED]"
                    records_updated += 1

            for row in self.store.onboarding_tasks.values():
                if row["employee_id"] == target_user_id:
                    row["employee_id"] = anonymized_ref
                    records_updated += 1

        erased_at = datetime.now(timezone.utc)
        self.event_logger.log_event(
            event_type="governance_event",
            actor_id=actor["user_id"],
            actor_role=actor["role"],
            details={
                "action": "erasure",
                "target_user_id": target_user_id,
                "records_updated": records_updated,
            },
        )

        return ErasureResponse(
            user_id=target_user_id,
            anonymized_at=erased_at,
            records_updated=records_updated,
        )

    def retention_cleanup(
        self,
        actor: dict[str, Any],
        retention_days: int,
        event_logger: EventLogger,
    ) -> RetentionCleanupResponse:
        if actor["role"] != Role.HR:
            raise HTTPException(status_code=403, detail="Only HR can run retention cleanup")
        if retention_days < 30:
            raise HTTPException(status_code=400, detail="Retention period must be at least 30 days")

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        anonymized_workflows = 0

        with self.store.lock:
            for row in self.store.leave_requests.values():
                if row["status"] in {"APPROVED", "REJECTED"} and datetime.fromisoformat(row["updated_at"]) < cutoff:
                    row["reason"] = "[REDACTED_RETENTION]"
                    anonymized_workflows += 1

            for row in self.store.document_requests.values():
                fulfilled_at = row.get("fulfilled_at")
                if fulfilled_at and datetime.fromisoformat(fulfilled_at) < cutoff:
                    row["purpose"] = "[REDACTED_RETENTION]"
                    anonymized_workflows += 1

        removed_events = event_logger.cleanup_older_than(retention_days)
        self.event_logger.log_event(
            event_type="governance_event",
            actor_id=actor["user_id"],
            actor_role=actor["role"],
            details={
                "action": "retention_cleanup",
                "retention_days": retention_days,
                "removed_events": removed_events,
                "workflow_records_anonymized": anonymized_workflows,
            },
        )

        return RetentionCleanupResponse(
            retention_days=retention_days,
            removed_events=removed_events,
            workflow_records_anonymized=anonymized_workflows,
        )
