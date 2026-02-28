from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.core.rbac import Role
from app.models.workflow import (
    DocumentRequestCreate,
    DocumentRequestRecord,
    DocumentStatus,
    LeaveDecisionRequest,
    LeaveRequestCreate,
    LeaveRequestRecord,
    LeaveStatus,
    OnboardingTaskRecord,
    OnboardingTriggerRequest,
    TaskStatus,
)
from app.repositories.data_store import DataStore
from app.services.analytics_service import EventLogger
from app.services.auth_service import AuthService
from app.services.governance_service import GovernanceService


class WorkflowService:
    def __init__(
        self,
        store: DataStore,
        event_logger: EventLogger,
        governance_service: GovernanceService,
        auth_service: AuthService,
    ) -> None:
        self.store = store
        self.event_logger = event_logger
        self.governance_service = governance_service
        self.auth_service = auth_service

    @staticmethod
    def _iso_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_leave_request(self, user: dict[str, Any], payload: LeaveRequestCreate) -> LeaveRequestRecord:
        self.governance_service.ensure_consent(user, purpose="leave_request")

        if payload.start_date < date.today() - timedelta(days=1):
            raise HTTPException(status_code=400, detail="Leave start_date cannot be in the past")

        approver_role = "MANAGER" if user["role"] == Role.EMPLOYEE else "HR"

        request_id = f"leave-{uuid4().hex[:10]}"
        now = self._iso_now()
        row = {
            "request_id": request_id,
            "employee_id": user["user_id"],
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
            "reason": payload.reason,
            "status": LeaveStatus.PENDING,
            "pending_approver_role": approver_role,
            "decision_notes": None,
            "created_at": now,
            "updated_at": now,
        }

        with self.store.lock:
            self.store.leave_requests[request_id] = row

        self.event_logger.log_event(
            event_type="workflow_action",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={"action": "leave_created", "request_id": request_id, "count": 1},
        )
        self.event_logger.log_event(
            event_type="automation_event",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={
                "action": "leave_auto_routed",
                "request_id": request_id,
                "action_count": 1,
                "target_approver_role": approver_role,
            },
        )

        return self._to_leave_model(row)

    def decide_leave_request(
        self,
        user: dict[str, Any],
        request_id: str,
        payload: LeaveDecisionRequest,
    ) -> LeaveRequestRecord:
        with self.store.lock:
            row = self.store.leave_requests.get(request_id)
            if not row:
                raise HTTPException(status_code=404, detail="Leave request not found")

            if row["status"] != LeaveStatus.PENDING:
                raise HTTPException(status_code=400, detail="Leave request is not pending")

            employee_id = row["employee_id"]
            if user["role"] == Role.MANAGER and not self.auth_service.is_manager_of(
                user["user_id"], employee_id
            ):
                raise HTTPException(status_code=403, detail="Manager can only approve team member leave")
            if user["role"] not in {Role.HR, Role.MANAGER}:
                raise HTTPException(status_code=403, detail="Only manager or HR can decide leave")

            row["status"] = LeaveStatus.APPROVED if payload.approve else LeaveStatus.REJECTED
            row["decision_notes"] = payload.notes
            row["pending_approver_role"] = "-"
            row["updated_at"] = self._iso_now()

        self.event_logger.log_event(
            event_type="workflow_action",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={
                "action": "leave_decision",
                "request_id": request_id,
                "decision": row["status"],
                "count": 1,
            },
        )

        return self._to_leave_model(row)

    def list_leave_requests(self, user: dict[str, Any]) -> list[LeaveRequestRecord]:
        with self.store.lock:
            rows = list(self.store.leave_requests.values())

        if user["role"] == Role.HR:
            return [self._to_leave_model(r) for r in rows]

        if user["role"] == Role.MANAGER:
            visible_ids = set(user.get("team_members", [])) | {user["user_id"]}
            return [self._to_leave_model(r) for r in rows if r["employee_id"] in visible_ids]

        return [self._to_leave_model(r) for r in rows if r["employee_id"] == user["user_id"]]

    def create_document_request(
        self,
        user: dict[str, Any],
        payload: DocumentRequestCreate,
    ) -> DocumentRequestRecord:
        self.governance_service.ensure_consent(user, purpose="document_request")

        request_id = f"doc-{uuid4().hex[:10]}"
        row = {
            "request_id": request_id,
            "employee_id": user["user_id"],
            "document_type": payload.document_type,
            "purpose": payload.purpose,
            "status": DocumentStatus.REQUESTED,
            "requested_at": self._iso_now(),
            "fulfilled_at": None,
        }

        with self.store.lock:
            self.store.document_requests[request_id] = row

        self.event_logger.log_event(
            event_type="workflow_action",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={"action": "document_requested", "request_id": request_id, "count": 1},
        )

        return self._to_document_model(row)

    def fulfill_document_request(
        self,
        user: dict[str, Any],
        request_id: str,
    ) -> DocumentRequestRecord:
        if user["role"] != Role.HR:
            raise HTTPException(status_code=403, detail="Only HR can fulfill document requests")

        with self.store.lock:
            row = self.store.document_requests.get(request_id)
            if not row:
                raise HTTPException(status_code=404, detail="Document request not found")
            row["status"] = DocumentStatus.FULFILLED
            row["fulfilled_at"] = self._iso_now()

        self.event_logger.log_event(
            event_type="workflow_action",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={"action": "document_fulfilled", "request_id": request_id, "count": 1},
        )

        return self._to_document_model(row)

    def list_document_requests(self, user: dict[str, Any]) -> list[DocumentRequestRecord]:
        with self.store.lock:
            rows = list(self.store.document_requests.values())

        if user["role"] == Role.HR:
            return [self._to_document_model(r) for r in rows]

        if user["role"] == Role.MANAGER:
            visible_ids = set(user.get("team_members", [])) | {user["user_id"]}
            return [self._to_document_model(r) for r in rows if r["employee_id"] in visible_ids]

        return [self._to_document_model(r) for r in rows if r["employee_id"] == user["user_id"]]

    def trigger_onboarding(
        self,
        user: dict[str, Any],
        payload: OnboardingTriggerRequest,
    ) -> list[OnboardingTaskRecord]:
        if user["role"] != Role.HR:
            raise HTTPException(status_code=403, detail="Only HR can trigger onboarding")

        with self.store.lock:
            if payload.employee_id not in self.store.users:
                raise HTTPException(status_code=404, detail="Employee not found")

        templates = [
            ("Complete I-9 verification", "HR", 0),
            ("Provision laptop and access accounts", "IT", 1),
            ("Schedule manager orientation", "MANAGER", 2),
            ("Acknowledge code of conduct", "EMPLOYEE", 1),
        ]

        created_rows: list[dict[str, Any]] = []
        now = self._iso_now()
        with self.store.lock:
            for title, owner_role, due_offset in templates:
                task_id = f"onb-{uuid4().hex[:10]}"
                row = {
                    "task_id": task_id,
                    "employee_id": payload.employee_id,
                    "title": title,
                    "owner_role": owner_role,
                    "due_date": (payload.start_date + timedelta(days=due_offset)).isoformat(),
                    "status": TaskStatus.OPEN,
                    "trigger_source": "ONBOARDING_TRIGGER",
                    "created_at": now,
                }
                self.store.onboarding_tasks[task_id] = row
                created_rows.append(row)

        self.event_logger.log_event(
            event_type="workflow_action",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={
                "action": "onboarding_triggered",
                "employee_id": payload.employee_id,
                "count": 1,
            },
        )
        self.event_logger.log_event(
            event_type="automation_event",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={
                "action": "onboarding_tasks_auto_created",
                "employee_id": payload.employee_id,
                "action_count": len(created_rows),
            },
        )

        return [self._to_task_model(r) for r in created_rows]

    def list_onboarding_tasks(self, user: dict[str, Any], employee_id: str | None = None) -> list[OnboardingTaskRecord]:
        with self.store.lock:
            rows = list(self.store.onboarding_tasks.values())

        if user["role"] == Role.HR:
            filtered = rows
        elif user["role"] == Role.MANAGER:
            visible_ids = set(user.get("team_members", [])) | {user["user_id"]}
            filtered = [r for r in rows if r["employee_id"] in visible_ids]
        else:
            filtered = [r for r in rows if r["employee_id"] == user["user_id"]]

        if employee_id:
            filtered = [r for r in filtered if r["employee_id"] == employee_id]

        return [self._to_task_model(r) for r in filtered]

    @staticmethod
    def _to_leave_model(row: dict[str, Any]) -> LeaveRequestRecord:
        return LeaveRequestRecord(
            request_id=row["request_id"],
            employee_id=row["employee_id"],
            start_date=date.fromisoformat(row["start_date"]),
            end_date=date.fromisoformat(row["end_date"]),
            reason=row["reason"],
            status=row["status"],
            pending_approver_role=row["pending_approver_role"],
            decision_notes=row.get("decision_notes"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _to_document_model(row: dict[str, Any]) -> DocumentRequestRecord:
        fulfilled_at = row.get("fulfilled_at")
        return DocumentRequestRecord(
            request_id=row["request_id"],
            employee_id=row["employee_id"],
            document_type=row["document_type"],
            purpose=row["purpose"],
            status=row["status"],
            requested_at=datetime.fromisoformat(row["requested_at"]),
            fulfilled_at=datetime.fromisoformat(fulfilled_at) if fulfilled_at else None,
        )

    @staticmethod
    def _to_task_model(row: dict[str, Any]) -> OnboardingTaskRecord:
        return OnboardingTaskRecord(
            task_id=row["task_id"],
            employee_id=row["employee_id"],
            title=row["title"],
            owner_role=row["owner_role"],
            due_date=date.fromisoformat(row["due_date"]),
            status=row["status"],
            trigger_source=row["trigger_source"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
