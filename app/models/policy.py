from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PolicyDocument(BaseModel):
    policy_id: str
    title: str
    category: str
    audience: str
    content: str
    tags: list[str] = Field(default_factory=list)
    effective_date: date
    last_updated: date


class PolicyCitation(BaseModel):
    policy_id: str
    title: str


class PolicyQueryRequest(BaseModel):
    question: str = Field(min_length=10, max_length=500)


class PolicyQueryResponse(BaseModel):
    response_id: str
    answer: str
    confidence: float
    citations: list[PolicyCitation]
    governance_notice: str


class PolicyFeedbackRequest(BaseModel):
    response_id: str
    accurate: bool
    comment: Optional[str] = Field(default=None, max_length=300)
