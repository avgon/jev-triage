"""Core triage classifier."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jev_triage.client import JevClient

DEFAULT_DEPARTMENTS = {
    "billing": "Payment, invoice, refund, subscription issues",
    "shipping": "Delivery, tracking, address, logistics problems",
    "technical": "Bugs, API errors, integration, performance issues",
    "sales": "Pricing, plans, enterprise inquiries, upgrades",
    "general": "General questions, feedback, other",
}


@dataclass
class TriageResult:
    """Structured triage output."""

    department: str
    urgency: int  # 0=low, 1=medium, 2=critical
    sentiment: str  # positive, negative, neutral
    frustrated: bool
    revenue_impact: bool
    language: str
    tags: list[str] = field(default_factory=list)
    extra: dict[str, float] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


class Triage:
    """Jev-powered ticket classifier.

    Args:
        departments: Dict of department_key -> description.
        extra_signals: Additional noul/choice/score questions to evaluate.
        api_key: TypeSafe API key (or set TYPESAFE_API_KEY env var).
        base_url: Custom API endpoint.
        model: Jev model name (default: jev-latest).
    """

    def __init__(
        self,
        departments: dict[str, str] | None = None,
        extra_signals: dict[str, dict[str, Any]] | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "jev-latest",
    ):
        self.departments = departments or DEFAULT_DEPARTMENTS
        self.extra_signals = extra_signals or {}
        self.client = JevClient(api_key=api_key, base_url=base_url, model=model)

    def classify(self, message: str) -> TriageResult:
        """Classify a single message/ticket."""
        questions: dict[str, Any] = {
            "department": {
                "type": "choice",
                "instructions": "Which department should handle this request?",
                "criteria": self.departments,
            },
            "urgency": {
                "type": "score",
                "instructions": "How urgent is this request?",
                "criteria": [
                    "Low priority — informational, no time pressure",
                    "Medium priority — needs attention within hours",
                    "Critical — immediate action required, system down or revenue loss",
                ],
            },
            "sentiment": {
                "type": "choice",
                "instructions": "What is the emotional tone of this message?",
                "criteria": {
                    "positive": "Happy, grateful, satisfied",
                    "negative": "Angry, frustrated, disappointed",
                    "neutral": "Factual, informational, no strong emotion",
                },
            },
            "frustrated": {
                "type": "noul",
                "instructions": "Is the customer frustrated, angry, or upset?",
            },
            "revenue_impact": {
                "type": "noul",
                "instructions": "Is this issue causing revenue loss or payment failure?",
            },
            "language": {
                "type": "choice",
                "instructions": "What language is this message written in?",
                "criteria": {
                    "en": "English",
                    "tr": "Turkish",
                    "de": "German",
                    "fr": "French",
                    "es": "Spanish",
                    "ja": "Japanese",
                    "zh": "Chinese",
                    "ar": "Arabic",
                    "other": "Other language",
                },
            },
            "tags": {
                "type": "choice",
                "instructions": "Primary topic tag for this ticket",
                "criteria": {
                    "refund": "Refund or money back request",
                    "login": "Authentication or access issue",
                    "bug": "Software bug or error",
                    "delivery": "Shipping or delivery issue",
                    "pricing": "Price or billing question",
                    "feature": "Feature request or suggestion",
                    "praise": "Positive feedback or thanks",
                    "other": "Other topic",
                },
            },
        }

        # Add extra signals
        for key, q in self.extra_signals.items():
            questions[key] = q

        answers = self.client.ask(state=f"Support ticket: {message}", questions=questions)

        # Extract extra signal values
        extra = {}
        for key in self.extra_signals:
            ans = answers.get(key, {})
            if isinstance(ans, (int, float)):
                extra[key] = round(float(ans), 2)
            elif isinstance(ans, dict):
                if "probability" in ans:
                    extra[key] = round(ans["probability"], 2)
                elif "choice" in ans:
                    extra[key] = ans["choice"]
                elif "score" in ans:
                    extra[key] = ans["score"]

        # Normalize noul fields (Jev may return float directly or nested)
        def _prob(ans: Any) -> float:
            if isinstance(ans, (int, float)):
                return float(ans)
            if isinstance(ans, dict):
                return float(ans.get("probability", 0))
            return 0.0

        tag = answers.get("tags", {}).get("choice", "other")

        return TriageResult(
            department=answers.get("department", {}).get("choice", "general"),
            urgency=_to_int(answers.get("urgency", {}).get("score", 0)),
            sentiment=answers.get("sentiment", {}).get("choice", "neutral"),
            frustrated=_prob(answers.get("frustrated", {})) > 0.5,
            revenue_impact=_prob(answers.get("revenue_impact", {})) > 0.5,
            language=answers.get("language", {}).get("choice", "en"),
            tags=[tag] if tag != "other" else [],
            extra=extra,
            raw=answers,
        )

    def classify_batch(self, messages: list[str]) -> list[TriageResult]:
        """Classify multiple messages."""
        return [self.classify(m) for m in messages]


def _to_int(val: Any) -> int:
    """Convert score to int, rounding floats."""
    try:
        return round(float(val))
    except (TypeError, ValueError):
        return 0
