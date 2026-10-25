from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ClaimKind(str, Enum):
    SOURCED_FACT = "sourced_fact"
    CALCULATION = "calculation"
    INFERENCE = "inference"


class Claim(BaseModel):
    """
    Structured debate claim submitted by Thor or Loki.
    """
    claim_id: str = Field(..., description="Unique claim ID, e.g. CLM-THOR-R1-01")
    agent: str = Field(..., description="'thor' or 'loki'")
    run_no: int = Field(default=1, ge=1)
    round_no: int = Field(default=1, ge=1)
    text: str = Field(..., min_length=10, description="Assertion statement")
    country: str = Field(..., description="Target nation or general")
    sector: str = Field(..., description="Target economic sector or general")
    estimate_low: Optional[float] = Field(default=None, description="Lower exposure bound")
    estimate_high: Optional[float] = Field(default=None, description="Upper exposure bound")
    unit: Optional[str] = Field(default="percent_change", description="Measurement unit (e.g. percent_change, metric_tons)")
    kind: ClaimKind = Field(default=ClaimKind.SOURCED_FACT)
    citations: List[str] = Field(..., min_length=1, description="List of DOC-ID#Pn or TABLE-ID#row references")
    method: Optional[str] = Field(default=None, description="Analytical tool or trade math method used")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="submitted", description="'submitted', 'attacked', 'defended', 'conceded', 'upheld', 'rejected'")


class Attack(BaseModel):
    """
    Cross-examination challenge targeting an opponent's claim.
    """
    attack_id: str = Field(..., description="e.g. ATK-LOKI-R2-01")
    from_agent: str = Field(..., description="'thor' or 'loki'")
    target_claim_id: str = Field(..., description="Claim ID being challenged")
    grounds: str = Field(..., description="'retracted', 'low_tier', 'wrong_event', 'bad_method', 'contradicted', 'stale'")
    evidence_refs: List[str] = Field(default_factory=list, description="Counter-evidence citations")
    text: str = Field(..., min_length=10, description="Detailed argument of the attack")


class Defence(BaseModel):
    """
    Rebuttal response to an attack: must provide new evidence OR concede.
    """
    defence_id: str = Field(..., description="e.g. DEF-THOR-R2-01")
    attack_id: str = Field(..., description="ID of the attack being answered")
    response_type: str = Field(..., description="'new_evidence' or 'concede'")
    new_refs: List[str] = Field(default_factory=list, description="Mandatory new citations if response_type == 'new_evidence'")
    text: str = Field(..., min_length=5, description="Defense explanation or concession rationale")


class Concession(BaseModel):
    """
    Formal admission that a claim has been invalidated by opposing evidence.
    """
    concession_id: str
    claim_id: str
    agent: str
    reason: str
