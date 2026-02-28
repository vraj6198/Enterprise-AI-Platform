from pydantic import BaseModel


class UsageMetrics(BaseModel):
    total_policy_queries: int
    unique_users: int
    queries_by_role: dict[str, int]


class AccuracyMetrics(BaseModel):
    feedback_samples: int
    accuracy_rate: float


class AutomationMetrics(BaseModel):
    total_workflow_actions: int
    automated_actions: int
    automation_rate: float


class KPIResponse(BaseModel):
    usage: UsageMetrics
    response_accuracy: AccuracyMetrics
    automation: AutomationMetrics
