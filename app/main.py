from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routers.analytics import router as analytics_router
from app.api.routers.auth import router as auth_router
from app.api.routers.governance import router as governance_router
from app.api.routers.policy import router as policy_router
from app.api.routers.ui import router as ui_router
from app.api.routers.workflows import router as workflows_router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="Enterprise HR AI Assistant with Governance & Workflow Automation",
    version="1.0.0",
    description=(
        "Portfolio project simulating enterprise HR AI implementation with policy guidance, "
        "RBAC, workflow automation, GDPR controls, and KPI analytics."
    ),
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Enterprise HR AI Assistant"}


app.include_router(ui_router)
app.include_router(auth_router)
app.include_router(policy_router)
app.include_router(workflows_router)
app.include_router(governance_router)
app.include_router(analytics_router)
