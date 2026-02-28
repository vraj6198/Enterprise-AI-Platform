from fastapi import APIRouter, Depends, Query

from app.api.deps import require_roles
from app.core.rbac import Role
from app.models.analytics import KPIResponse
from app.services.container import analytics_service


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/kpis", response_model=KPIResponse)
def get_kpis(
    current_user: dict = Depends(require_roles([Role.HR, Role.MANAGER])),
) -> KPIResponse:
    _ = current_user
    return analytics_service.get_kpis()


@router.get("/events")
def get_recent_events(
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: dict = Depends(require_roles([Role.HR])),
) -> list[dict]:
    _ = current_user
    return analytics_service.get_recent_events(limit)
