from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.core.rbac import Role
from app.models.workflow import (
    DocumentRequestCreate,
    DocumentRequestRecord,
    LeaveDecisionRequest,
    LeaveRequestCreate,
    LeaveRequestRecord,
    OnboardingTaskRecord,
    OnboardingTriggerRequest,
)
from app.services.container import workflow_service


router = APIRouter(prefix="/workflows", tags=["Workflow Automation"])


@router.post("/leave", response_model=LeaveRequestRecord)
def create_leave_request(
    payload: LeaveRequestCreate,
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER, Role.EMPLOYEE])),
) -> LeaveRequestRecord:
    return workflow_service.create_leave_request(current_user, payload)


@router.get("/leave", response_model=list[LeaveRequestRecord])
def list_leave_requests(
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER, Role.EMPLOYEE])),
) -> list[LeaveRequestRecord]:
    return workflow_service.list_leave_requests(current_user)


@router.post("/leave/{request_id}/decision", response_model=LeaveRequestRecord)
def decide_leave_request(
    request_id: str,
    payload: LeaveDecisionRequest,
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER])),
) -> LeaveRequestRecord:
    return workflow_service.decide_leave_request(current_user, request_id, payload)


@router.post("/documents/request", response_model=DocumentRequestRecord)
def create_document_request(
    payload: DocumentRequestCreate,
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER, Role.EMPLOYEE])),
) -> DocumentRequestRecord:
    return workflow_service.create_document_request(current_user, payload)


@router.get("/documents", response_model=list[DocumentRequestRecord])
def list_document_requests(
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER, Role.EMPLOYEE])),
) -> list[DocumentRequestRecord]:
    return workflow_service.list_document_requests(current_user)


@router.post("/documents/{request_id}/fulfill", response_model=DocumentRequestRecord)
def fulfill_document_request(
    request_id: str,
    current_user: dict = Depends(require_roles([Role.HR])),
) -> DocumentRequestRecord:
    return workflow_service.fulfill_document_request(current_user, request_id)


@router.post("/onboarding/trigger", response_model=list[OnboardingTaskRecord])
def trigger_onboarding(
    payload: OnboardingTriggerRequest,
    current_user: dict = Depends(require_roles([Role.HR])),
) -> list[OnboardingTaskRecord]:
    return workflow_service.trigger_onboarding(current_user, payload)


@router.get("/onboarding", response_model=list[OnboardingTaskRecord])
def list_onboarding_tasks(
    employee_id: Optional[str] = None,
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER, Role.EMPLOYEE])),
) -> list[OnboardingTaskRecord]:
    return workflow_service.list_onboarding_tasks(current_user, employee_id)
