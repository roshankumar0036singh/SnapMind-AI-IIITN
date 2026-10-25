"""
src/schemas/debate.py
=====================
Schemas for the open-ended, state-driven convergence debate loop.

Replaces the old fixed 'max_rounds' / 'max_runs' approach.
The deterministic runner reads these schemas to decide termination;
no LLM agent may touch them directly.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Debate Budget — independent safety caps per resource dimension
# ---------------------------------------------------------------------------

class DebateBudget(BaseModel):
    """
    Explicit, orthogonal safety budgets that bound the open-ended debate loop.
    Every limit is a hard upper bound. Hitting any one triggers termination.
    """
    max_debate_turns: int = Field(
        default=12,
        ge=2,
        description=(
            "Absolute maximum total debate turns (claims + attacks + defences = 1 turn each). "
            "Hard ceiling. Debate ends after this many individual agent actions."
        ),
    )
    max_tool_calls: int = Field(
        default=40,
        ge=4,
        description="Maximum combined tool calls across all agents during debate.",
    )
    max_tokens: int = Field(
        default=120_000,
        ge=1_000,
        description="Maximum total tokens consumed by LLM calls during debate.",
    )
    max_wall_seconds: float = Field(
        default=300.0,
        ge=10.0,
        description="Maximum wall-clock seconds for the entire debate phase.",
    )
    max_stable_cycles: int = Field(
        default=2,
        ge=1,
        description=(
            "Maximum consecutive cycles with identical canonical state fingerprint "
            "before declaring the debate stalled."
        ),
    )
    max_no_progress_cycles: int = Field(
        default=3,
        ge=1,
        description=(
            "Maximum consecutive cycles where no new claims, attacks, or defences were added, "
            "before declaring the debate stalled due to no progress."
        ),
    )
    # Runtime counters (mutated by the runner, never by LLMs)
    turns_used: int = Field(default=0, ge=0)
    tool_calls_used: int = Field(default=0, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    wall_seconds_used: float = Field(default=0.0, ge=0.0)
    stable_cycles: int = Field(default=0, ge=0)
    no_progress_cycles: int = Field(default=0, ge=0)
    evidence_runs: int = Field(
        default=0,
        ge=0,
        description="Evidence gathering runs executed so far.",
    )
    max_evidence_runs: int = Field(
        default=3,
        ge=1,
        description="Hard cap on evidence gathering runs (Heimdall send-backs).",
    )

    # Which budget was hit (set on termination)
    limit_hit: Optional[str] = Field(
        default=None,
        description="'max_debate_turns' | 'max_tool_calls' | 'max_tokens' | 'max_wall_seconds' | 'evidence_run_budget_exhausted' | 'converged' | 'stalled' | None",
    )

    def is_any_limit_hit(self) -> bool:
        """Return True if any hard budget has been exhausted."""
        return (
            self.turns_used >= self.max_debate_turns
            or self.tool_calls_used >= self.max_tool_calls
            or self.tokens_used >= self.max_tokens
            or self.wall_seconds_used >= self.max_wall_seconds
            or self.evidence_runs >= self.max_evidence_runs
        )

    def is_stalled(self) -> bool:
        """Return True if the debate is spinning without progress."""
        return (
            self.stable_cycles >= self.max_stable_cycles
            or self.no_progress_cycles >= self.max_no_progress_cycles
        )


# ---------------------------------------------------------------------------
# Debate Termination State — the judicial record of how debate ended
# ---------------------------------------------------------------------------

class DebateTerminationReason(str, Enum):
    CONVERGED = "converged"
    STALLED = "stalled"
    LIMIT_HIT = "limit_hit"
    CLOSED_INCOMPLETE = "closed_incomplete"


class DebateTerminationState(BaseModel):
    """
    Judicial record explaining exactly how and why the debate terminated.
    Written by the deterministic runner, never by LLM agents.
    """
    reason: DebateTerminationReason
    budget_hit: Optional[str] = None
    final_fingerprint: Optional[str] = None
    total_turns: int = 0
    total_tool_calls: int = 0
    total_tokens: int = 0
    wall_seconds: float = 0.0
    annotation: str = Field(default="")
    closed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Debate Round Record — one cycle of debate actions
# ---------------------------------------------------------------------------

class DebatePhase(str, Enum):
    CLAIM_SYNTHESIS = "claim_synthesis"
    CROSS_EXAMINATION = "cross_examination"
    REBUTTAL = "rebuttal"
    CONCESSION = "concession"


class DebateTurnRecord(BaseModel):
    """
    Lightweight record of one agent turn appended to the debate log.
    Used to compute fingerprints and detect progress.
    """
    turn_no: int
    cycle_no: int
    phase: DebatePhase
    agent: str
    action: str
    claims_count: int = 0
    attacks_count: int = 0
    defences_count: int = 0
    concessions_count: int = 0
    tool_calls_used: int = 0
    tokens_used: int = 0
    fingerprint_before: Optional[str] = None
    fingerprint_after: Optional[str] = None
