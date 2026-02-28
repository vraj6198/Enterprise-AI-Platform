from app.core.config import settings
from app.repositories.data_store import DataStore
from app.services.analytics_service import AnalyticsService, EventLogger
from app.services.auth_service import AuthService
from app.services.governance_service import GovernanceService
from app.services.policy_service import PolicyService
from app.services.workflow_service import WorkflowService


store = DataStore()
event_logger = EventLogger()

analytics_service = AnalyticsService(event_logger=event_logger)
auth_service = AuthService(store=store, event_logger=event_logger)
governance_service = GovernanceService(store=store, event_logger=event_logger)
policy_service = PolicyService(
    policy_path=settings.policy_dataset_path,
    store=store,
    event_logger=event_logger,
    governance_service=governance_service,
)
workflow_service = WorkflowService(
    store=store,
    event_logger=event_logger,
    governance_service=governance_service,
    auth_service=auth_service,
)
