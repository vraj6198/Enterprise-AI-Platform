from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ConsentUpdateRequest(BaseModel):
    gdpr_consent: bool


class ErasureResponse(BaseModel):
    user_id: str
    anonymized_at: datetime
    records_updated: int


class RetentionCleanupResponse(BaseModel):
    retention_days: int
    removed_events: int
    workflow_records_anonymized: int


class SubjectAccessResponse(BaseModel):
    user_profile: dict[str, Any]
    leave_requests: list[dict[str, Any]]
    document_requests: list[dict[str, Any]]
    onboarding_tasks: list[dict[str, Any]]
