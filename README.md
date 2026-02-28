# Enterprise AI Assistant with Governance & Workflow Automation

Portfolio-ready FastAPI project that simulates a real enterprise HR AI + HRIS implementation with policy intelligence, workflow automation, RBAC, GDPR-aligned controls, and KPI tracking.

## Suggested GitHub Description

Enterprise-grade HR AI Assistant built with FastAPI: policy Q&A, role-based access control, HRIS workflow automation, GDPR governance logic, and KPI analytics.

## Live Demo

- Public UI (working link): `https://7391f7cae445c1.lhr.life/ui`
- Public API docs: `https://7391f7cae445c1.lhr.life/docs`
- Local UI: `http://127.0.0.1:8000/ui`
- Local API docs: `http://127.0.0.1:8000/docs`

Last verified working: **February 28, 2026**.

Note: public tunnel links are temporary and may rotate when the tunnel restarts.

## Business Problem

HR teams need to answer policy questions quickly, execute repetitive HR operations consistently, and remain compliant with privacy requirements.

Common challenges:
- inconsistent manager policy interpretation,
- manual HR request handling,
- weak audit trails,
- poor visibility into AI usefulness and automation impact.

## Solution Overview

This solution combines an AI-style policy assistant with operational HR workflows and governance controls.

Core features:
- AI-powered HR policy assistant with confidence score and citations.
- RBAC for `HR`, `MANAGER`, and `EMPLOYEE` roles.
- HRIS-style workflows:
  - leave request + approval chain,
  - document request + HR fulfillment,
  - onboarding trigger + auto task creation.
- Governance layer:
  - GDPR consent checks,
  - subject access request,
  - data erasure/anonymization,
  - retention cleanup logic.
- KPI analytics:
  - usage,
  - response accuracy,
  - automation rate.
- Browser-based UI connected to live APIs.

## Technical Architecture

```text
[Web UI (/ui)]
      |
      v
[FastAPI Routers]
  /auth
  /policy
  /workflows
  /governance
  /analytics
      |
      v
[Service Layer]
  AuthService
  PolicyService
  WorkflowService
  GovernanceService
  AnalyticsService
      |
      v
[Data Layer]
  In-memory DataStore
  Policy JSON dataset
  JSONL event log for analytics/audit
```

## Governance Controls

- Consent gate before policy/workflow processing.
- Data minimization in policy query logging (PII-style redaction patterns).
- Subject Access Request endpoint for HR or self-access.
- Right to erasure via anonymization workflow.
- Retention cleanup for stale events and workflow data redaction.
- Human oversight statement in AI policy responses.

## KPI / Impact Metrics

`GET /analytics/kpis` provides:
- Usage:
  - total policy queries,
  - unique users,
  - queries by role.
- Response accuracy:
  - feedback sample count,
  - accuracy rate from user feedback.
- Automation:
  - total workflow actions,
  - automated actions,
  - automation rate.

## Folder Structure

```text
.
├── app
│   ├── api
│   │   ├── deps.py
│   │   └── routers
│   │       ├── analytics.py
│   │       ├── auth.py
│   │       ├── governance.py
│   │       ├── policy.py
│   │       ├── ui.py
│   │       └── workflows.py
│   ├── core
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── rbac.py
│   │   └── security.py
│   ├── data
│   │   └── hr_policies.json
│   ├── models
│   │   ├── analytics.py
│   │   ├── auth.py
│   │   ├── governance.py
│   │   ├── policy.py
│   │   └── workflow.py
│   ├── repositories
│   │   └── data_store.py
│   ├── services
│   │   ├── analytics_service.py
│   │   ├── auth_service.py
│   │   ├── container.py
│   │   ├── governance_service.py
│   │   ├── policy_service.py
│   │   └── workflow_service.py
│   ├── static
│   │   ├── css/style.css
│   │   └── js/app.js
│   ├── templates
│   │   └── index.html
│   └── main.py
├── data
├── requirements.txt
└── README.md
```

## Demo Credentials

- `hr_admin / hr123`
- `mgr_jane / manager123`
- `emp_alex / employee123`
- `emp_sam / employee456`

## Setup Instructions

1. Create venv and install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run app:

```bash
uvicorn app.main:app --reload
```

3. Open UI:

```text
http://127.0.0.1:8000/ui
```

## API Quick Start

1. `POST /auth/token`
2. `POST /policy/query`
3. `POST /workflows/leave`
4. `POST /workflows/leave/{request_id}/decision`
5. `POST /workflows/documents/request`
6. `POST /workflows/onboarding/trigger`
7. `PATCH /governance/consent/{target_user_id}`
8. `GET /analytics/kpis`

## Interview Positioning

This project is designed to discuss in HR AI / HRIS interviews:
- enterprise RBAC boundary design,
- AI assistant governance (advisory + human-in-loop),
- workflow orchestration and automation metrics,
- GDPR-aligned operational controls,
- practical observability via event logging and KPIs.

## Production Upgrade Path

- Replace in-memory store with PostgreSQL.
- Add SSO (OIDC/SAML) and enterprise identity provisioning.
- Replace lexical policy retrieval with embedding search + vector DB.
- Add test suite (unit + integration + contract tests).
- Add queue-based async processing for heavy workflow automations.
