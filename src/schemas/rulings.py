from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RulingOutcome(str, Enum):
    UPHELD = "upheld"
    REJECTED = "rejected"
    CONCEDED = "conceded"
    CONTESTED = "contested"


class RulingBasis(str, Enum):
    SOURCED_FACT = "sourced_fact"
    CALCULATION = "calculation"
    INFERENCE = "inference"


class Ruling(BaseModel):
    """
    Judicial decision issued by Odin for an individual claim.
    """
    ruling_id: str = Field(..., description="e.g. RUL-ODIN-01")
    claim_id: str = Field(..., description="Target claim ID")
    outcome: RulingOutcome
    basis: RulingBasis
    reasoning: str = Field(..., min_length=10, description="Judicial explanation citing verification findings")
    refs_checked: List[str] = Field(default_factory=list, description="Citations verified by Odin")


class ClassificationSummary(BaseModel):
    """
    Sorting of all findings for executive briefing (FR4.2 & FR8.1).
    """
    established: List[str] = Field(default_factory=list, description="Claim IDs ruled UPHELD / fact-grounded")
    contested: List[str] = Field(default_factory=list, description="Claim IDs with unresolved contradictions")
    conceded: List[str] = Field(default_factory=list, description="Claim IDs formally conceded by an agent")


class CountrySectorRange(BaseModel):
    """
    Calibrated exposure range per country and sector (FR7.3 & FR8.2).
    """
    country: str
    sector: str
    unit: str = "percent_change"
    thor_low: Optional[float] = None
    thor_high: Optional[float] = None
    loki_low: Optional[float] = None
    loki_high: Optional[float] = None
    odin_low: float = Field(..., description="Judicially synthesized lower bound")
    odin_high: float = Field(..., description="Judicially synthesized upper bound")
    basis: str = Field(..., description="Rationale explaining how Odin combined Thor and Loki evidence")
