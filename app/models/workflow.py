from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DocumentStatus(str, Enum):
    REQUESTED = "REQUESTED"
    FULFILLED = "FULFILLED"


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    DONE = "DONE"


class LeaveRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=5, max_length=250)

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaveRequestCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaveDecisionRequest(BaseModel):
    approve: bool
    notes: Optional[str] = Field(default=None, max_length=300)


class LeaveRequestRecord(BaseModel):
    request_id: str
    employee_id: str
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus
    pending_approver_role: str
    decision_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentRequestCreate(BaseModel):
    document_type: str = Field(min_length=3, max_length=80)
    purpose: str = Field(min_length=5, max_length=200)


class DocumentRequestRecord(BaseModel):
    request_id: str
    employee_id: str
    document_type: str
    purpose: str
    status: DocumentStatus
    requested_at: datetime
    fulfilled_at: Optional[datetime] = None


class OnboardingTriggerRequest(BaseModel):
    employee_id: str
    start_date: date


class OnboardingTaskRecord(BaseModel):
    task_id: str
    employee_id: str
    title: str
    owner_role: str
    due_date: date
    status: TaskStatus
    trigger_source: str
    created_at: datetime
