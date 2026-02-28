from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.models.policy import (
    PolicyCitation,
    PolicyDocument,
    PolicyFeedbackRequest,
    PolicyQueryResponse,
)
from app.repositories.data_store import DataStore
from app.services.analytics_service import EventLogger
from app.services.governance_service import GovernanceService

TOKEN_PATTERN = re.compile(r"[a-zA-Z]{2,}")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
NUMBER_PATTERN = re.compile(r"\b\d{6,}\b")


class PolicyService:
    def __init__(
        self,
        policy_path: Path,
        store: DataStore,
        event_logger: EventLogger,
        governance_service: GovernanceService,
    ) -> None:
        self.policy_path = policy_path
        self.store = store
        self.event_logger = event_logger
        self.governance_service = governance_service
        self._policies = self._load_policies()
        self._index = {
            p.policy_id: self._tokenize(" ".join([p.title, p.category, p.audience, p.content, " ".join(p.tags)]))
            for p in self._policies
        }

    def _load_policies(self) -> list[PolicyDocument]:
        if not self.policy_path.exists():
            raise RuntimeError(f"Policy dataset not found: {self.policy_path}")
        raw = json.loads(self.policy_path.read_text(encoding="utf-8"))
        return [PolicyDocument(**row) for row in raw]

    @staticmethod
    def _tokenize(text: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for token in TOKEN_PATTERN.findall(text.lower()):
            counts[token] = counts.get(token, 0) + 1
        return counts

    @staticmethod
    def _cosine_similarity(vec_a: dict[str, int], vec_b: dict[str, int]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        keys = set(vec_a) & set(vec_b)
        dot = sum(vec_a[k] * vec_b[k] for k in keys)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _sanitize_question(question: str) -> str:
        question = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", question)
        question = NUMBER_PATTERN.sub("[REDACTED_NUMBER]", question)
        return question

    def list_policies(self) -> list[PolicyDocument]:
        return self._policies

    def query(self, user: dict[str, Any], question: str) -> PolicyQueryResponse:
        self.governance_service.ensure_consent(user, purpose="policy_assistance")

        q_tokens = self._tokenize(question)
        scored: list[tuple[PolicyDocument, float]] = []

        for policy in self._policies:
            base_score = self._cosine_similarity(q_tokens, self._index[policy.policy_id])
            role_keyword = user["role"].lower()
            audience_boost = 0.08 if role_keyword in policy.audience.lower() else 0.0
            tag_boost = 0.03 * sum(
                1 for t in policy.tags if t.lower() in question.lower()
            )
            score = base_score + audience_boost + tag_boost
            scored.append((policy, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_matches = scored[:2]
        top_policy, top_score = top_matches[0]

        if top_score < 0.08:
            answer = (
                "No direct policy match was found with high confidence. "
                "Escalate to HR for interpretation and policy exception handling."
            )
            citations = [PolicyCitation(policy_id=top_policy.policy_id, title=top_policy.title)]
            confidence = round(max(top_score, 0.2), 3)
        else:
            answer = (
                f"Based on '{top_policy.title}', {top_policy.content} "
                "Follow the documented approval chain and record all actions in the HRIS workflow log."
            )
            citations = [
                PolicyCitation(policy_id=p.policy_id, title=p.title)
                for p, _ in top_matches
            ]
            confidence = round(min(0.99, top_score + 0.25), 3)

        response_id = f"pol-{uuid4().hex[:12]}"
        with self.store.lock:
            self.store.policy_responses[response_id] = {
                "user_id": user["user_id"],
                "question": self._sanitize_question(question),
                "citations": [c.policy_id for c in citations],
                "confidence": confidence,
            }

        self.event_logger.log_event(
            event_type="policy_query",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={
                "response_id": response_id,
                "question": self._sanitize_question(question),
                "confidence": confidence,
                "citations": [c.policy_id for c in citations],
            },
        )

        return PolicyQueryResponse(
            response_id=response_id,
            answer=answer,
            confidence=confidence,
            citations=citations,
            governance_notice=(
                "Output is policy guidance only. Personal data is redacted in analytics logs and subject to GDPR controls."
            ),
        )

    def record_feedback(self, user: dict[str, Any], payload: PolicyFeedbackRequest) -> dict[str, str]:
        with self.store.lock:
            exists = payload.response_id in self.store.policy_responses
        if not exists:
            raise HTTPException(status_code=404, detail="response_id not found")

        self.event_logger.log_event(
            event_type="policy_feedback",
            actor_id=user["user_id"],
            actor_role=user["role"],
            details={
                "response_id": payload.response_id,
                "accurate": payload.accurate,
                "comment": payload.comment or "",
            },
        )

        return {"message": "Feedback recorded"}
