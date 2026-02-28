from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_roles
from app.core.rbac import Role
from app.models.policy import (
    PolicyDocument,
    PolicyFeedbackRequest,
    PolicyQueryRequest,
    PolicyQueryResponse,
)
from app.services.container import policy_service


router = APIRouter(prefix="/policy", tags=["Policy Assistant"])


@router.get("/documents", response_model=list[PolicyDocument])
def list_policy_documents(
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER, Role.EMPLOYEE])),
) -> list[PolicyDocument]:
    _ = current_user
    return policy_service.list_policies()


@router.post("/query", response_model=PolicyQueryResponse)
def query_policy(
    payload: PolicyQueryRequest,
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER, Role.EMPLOYEE])),
) -> PolicyQueryResponse:
    return policy_service.query(current_user, payload.question)


@router.post("/feedback")
def submit_policy_feedback(
    payload: PolicyFeedbackRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    return policy_service.record_feedback(current_user, payload)
