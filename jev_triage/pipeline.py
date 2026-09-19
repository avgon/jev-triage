"""Pipeline: chain triage with escalation rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jev_triage.core import Triage, TriageResult


@dataclass
class EscalationRule:
    """A rule that overrides the default route when conditions match."""

    route: str
    urgency: int | None = None
    frustrated: bool | None = None
    revenue_impact: bool | None = None
    sentiment: str | None = None
    department: str | None = None

    def matches(self, result: TriageResult) -> bool:
        checks = []
        if self.urgency is not None:
            checks.append(result.urgency >= self.urgency)
        if self.frustrated is not None:
            checks.append(result.frustrated == self.frustrated)
        if self.revenue_impact is not None:
            checks.append(result.revenue_impact == self.revenue_impact)
        if self.sentiment is not None:
            checks.append(result.sentiment == self.sentiment)
        if self.department is not None:
            checks.append(result.department == self.department)
        return bool(checks) and all(checks)

    def describe(self) -> str:
        parts = []
        if self.urgency is not None:
            parts.append(f"urgency>={self.urgency}")
        if self.frustrated is not None:
            parts.append("frustrated" if self.frustrated else "not_frustrated")
        if self.revenue_impact is not None:
            parts.append("revenue_impact" if self.revenue_impact else "no_revenue_impact")
        if self.sentiment is not None:
            parts.append(f"sentiment={self.sentiment}")
        if self.department is not None:
            parts.append(f"dept={self.department}")
        return " + ".join(parts) or "always"


@dataclass
class PipelineResult:
    """Output of a pipeline run."""

    triage: TriageResult
    final_route: str
    applied_rule: str | None = None


class Pipeline:
    """Chain triage classification with routing rules.

    Args:
        triage: A configured Triage instance.
        rules: Ordered list of escalation rules (first match wins).
        default_route: Fallback route when no rules match.
    """

    def __init__(
        self,
        triage: Triage | None = None,
        rules: list[EscalationRule] | None = None,
        default_route: str = "general_queue",
        **triage_kwargs: Any,
    ):
        self.triage = triage or Triage(**triage_kwargs)
        self.rules = rules or []
        self.default_route = default_route

    def process(self, message: str) -> PipelineResult:
        """Classify and route a single message."""
        result = self.triage.classify(message)

        for rule in self.rules:
            if rule.matches(result):
                return PipelineResult(
                    triage=result,
                    final_route=rule.route,
                    applied_rule=rule.describe(),
                )

        return PipelineResult(
            triage=result,
            final_route=self.default_route,
            applied_rule=None,
        )

    def process_batch(self, messages: list[str]) -> list[PipelineResult]:
        """Process multiple messages."""
        return [self.process(m) for m in messages]
