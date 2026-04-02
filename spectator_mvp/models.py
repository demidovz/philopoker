from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentProfile:
    name: str
    role: str
    mission: str
    style: str


@dataclass
class MoveRecord:
    actor: str
    kind: str
    text: str


@dataclass
class RoundVerdict:
    status: str
    rationale: str
    new_claim: str | None = None
    refined_claim: str | None = None
    contradiction_found: bool = False
    winner: str | None = None
    team: str | None = None
    points: dict[str, int] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    human_status: str | None = None


@dataclass
class DebateState:
    current_claim: str
    initial_claim: str | None = None
    history: list[MoveRecord] = field(default_factory=list)
    round_summaries: list[str] = field(default_factory=list)
    round_winners: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)
    child_summary: str = ""

    def compact_history(self, limit: int = 8) -> str:
        if not self.history:
            return "История пока пуста."
        relevant = self.history[-limit:]
        return "\n".join(
            f"- {item.actor} [{item.kind}]: {item.text}" for item in relevant
        )
