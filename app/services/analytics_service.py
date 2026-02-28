from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from app.core.config import settings
from app.models.analytics import (
    AccuracyMetrics,
    AutomationMetrics,
    KPIResponse,
    UsageMetrics,
)


class EventLogger:
    def __init__(self, event_path: Path | None = None) -> None:
        self.event_path = event_path or settings.event_log_path
        self.event_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

    def log_event(
        self,
        event_type: str,
        actor_id: str,
        actor_role: str,
        details: dict[str, Any],
    ) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "details": details,
        }
        line = json.dumps(payload)
        with self.lock:
            with self.event_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    def read_events(self) -> list[dict[str, Any]]:
        if not self.event_path.exists():
            return []

        with self.lock:
            lines = self.event_path.read_text(encoding="utf-8").splitlines()

        events: list[dict[str, Any]] = []
        for raw in lines:
            if not raw.strip():
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return events

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.read_events()[-limit:]

    def cleanup_older_than(self, retention_days: int) -> int:
        if retention_days < 1:
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        kept: list[str] = []
        removed = 0

        if not self.event_path.exists():
            return 0

        with self.lock:
            lines = self.event_path.read_text(encoding="utf-8").splitlines()
            for raw in lines:
                if not raw.strip():
                    continue
                try:
                    event = json.loads(raw)
                    ts = datetime.fromisoformat(event["timestamp"])
                except Exception:
                    kept.append(raw)
                    continue

                if ts >= cutoff:
                    kept.append(raw)
                else:
                    removed += 1

            self.event_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

        return removed


class AnalyticsService:
    def __init__(self, event_logger: EventLogger) -> None:
        self.event_logger = event_logger

    def get_kpis(self) -> KPIResponse:
        events = self.event_logger.read_events()

        usage_events = [e for e in events if e.get("event_type") == "policy_query"]
        usage_by_role = Counter(e.get("actor_role", "UNKNOWN") for e in usage_events)

        feedback_events = [e for e in events if e.get("event_type") == "policy_feedback"]
        accurate_count = sum(
            1 for e in feedback_events if bool(e.get("details", {}).get("accurate"))
        )
        feedback_total = len(feedback_events)

        manual_workflow_actions = [
            e for e in events if e.get("event_type") == "workflow_action"
        ]
        automated_events = [e for e in events if e.get("event_type") == "automation_event"]

        manual_count = sum(int(e.get("details", {}).get("count", 1)) for e in manual_workflow_actions)
        automated_count = sum(
            int(e.get("details", {}).get("action_count", 1)) for e in automated_events
        )
        total_actions = manual_count + automated_count

        usage = UsageMetrics(
            total_policy_queries=len(usage_events),
            unique_users=len(set(e.get("actor_id") for e in usage_events)),
            queries_by_role=dict(usage_by_role),
        )
        accuracy = AccuracyMetrics(
            feedback_samples=feedback_total,
            accuracy_rate=round((accurate_count / feedback_total), 4)
            if feedback_total
            else 0.0,
        )
        automation = AutomationMetrics(
            total_workflow_actions=total_actions,
            automated_actions=automated_count,
            automation_rate=round((automated_count / total_actions), 4)
            if total_actions
            else 0.0,
        )

        return KPIResponse(usage=usage, response_accuracy=accuracy, automation=automation)

    def get_recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.event_logger.recent_events(limit=limit)
