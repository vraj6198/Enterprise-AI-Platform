from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, require_roles
from app.core.rbac import Role
from app.models.governance import (
    ConsentUpdateRequest,
    ErasureResponse,
    RetentionCleanupResponse,
    SubjectAccessResponse,
)
from app.models.auth import UserPublic
from app.services.container import auth_service, event_logger, governance_service


router = APIRouter(prefix="/governance", tags=["Governance"])


@router.patch("/consent/{target_user_id}", response_model=UserPublic)
def update_consent(
    target_user_id: str,
    payload: ConsentUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> UserPublic:
    updated = governance_service.update_consent(current_user, target_user_id, payload.gdpr_consent)
    return auth_service.as_public(updated)


@router.get("/subject-access/{target_user_id}", response_model=SubjectAccessResponse)
def subject_access_request(
    target_user_id: str,
    current_user: dict = Depends(get_current_user),
) -> SubjectAccessResponse:
    return governance_service.subject_access_request(current_user, target_user_id)


@router.post("/erase/{target_user_id}", response_model=ErasureResponse)
def erase_user_data(
    target_user_id: str,
    current_user: dict = Depends(require_roles([Role.HR])),
) -> ErasureResponse:
    return governance_service.erase_user_data(current_user, target_user_id)


@router.post("/retention/cleanup", response_model=RetentionCleanupResponse)
def run_retention_cleanup(
    retention_days: int = Query(default=365, ge=30, le=3650),
    current_user: dict = Depends(require_roles([Role.HR])),
) -> RetentionCleanupResponse:
    return governance_service.retention_cleanup(current_user, retention_days, event_logger)
