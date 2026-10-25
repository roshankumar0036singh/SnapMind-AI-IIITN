from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.schemas.ingest import IngestReport
from src.schemas.claims import Claim, Attack, Defence
from src.schemas.rulings import Ruling, ClassificationSummary, CountrySectorRange


class CaseStatus(str, Enum):
    OPEN = "open"
    REJECTED = "rejected"
    CLOSED = "closed"
    CLOSED_INCOMPLETE = "closed_incomplete"


class EventScope(BaseModel):
    """
    Scope determined by Heimdall from user question.
    """
    event_id: str = Field(..., description="e.g. 'E5'")
    event_name: str
    target_countries: List[str] = Field(default_factory=list)
    target_sectors: List[str] = Field(default_factory=list)
    as_of_date: date


class VerificationVerdict(BaseModel):
    """
    Event verification result from Heimdall (Acceptance Check 1).
    """
    verdict: str = Field(..., description="'real', 'rumour', or 'unverifiable'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    supporting_docs: List[str] = Field(default_factory=list)
    retractions: List[str] = Field(default_factory=list)
    message_to_user: str


class RunRecord(BaseModel):
    """
    Snapshot of an individual trial run (Run 1 or Run 2).
    """
    run_no: int = Field(default=1, ge=1)
    evidence_index: List[str] = Field(default_factory=list)
    side_status: Dict[str, str] = Field(default_factory=lambda: {"thor": "active", "loki": "active"})
    claims: List[Claim] = Field(default_factory=list)
    attacks: List[Attack] = Field(default_factory=list)
    defences: List[Defence] = Field(default_factory=list)
    rulings: List[Ruling] = Field(default_factory=list)
    classification: Optional[ClassificationSummary] = None
    ranges: List[CountrySectorRange] = Field(default_factory=list)
    sufficiency: str = Field(default="pending", description="'sufficient', 'send_back', or 'incomplete'")
    missing: List[str] = Field(default_factory=list, description="Missing evidence categories if send_back")


class CaseFile(BaseModel):
    """
    The central blackboard object: single source of truth shared across all agents.
    """
    case_id: str = Field(..., description="Unique case identifier")
    question: str = Field(..., description="User question")
    as_of: date = Field(..., description="Simulated Clock date")
    status: CaseStatus = Field(default=CaseStatus.OPEN)
    scope: Optional[EventScope] = None
    verification: Optional[VerificationVerdict] = None
    ingest_report: Optional[IngestReport] = None
    runs: List[RunRecord] = Field(default_factory=list)
    limits: Dict[str, Any] = Field(default_factory=lambda: {
        "max_runs": 2,
        "max_rounds": 2,
        "tool_calls_used": 0,
        "tokens_used": 0,
        "limit_hit": False
    })
    final_briefing: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
