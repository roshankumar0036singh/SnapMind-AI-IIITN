from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    SEARCH_STRATEGY = "search_strategy"
    SOURCE_LESSON = "source_lesson"
    CALCULATION_METHOD = "calculation_method"
    VERIFICATION_RULE = "verification_rule"
    RULING_PRECEDENT = "ruling_precedent"


class MemoryScope(str, Enum):
    GLOBAL = "global"
    EVENT = "event"
    COUNTRY = "country"
    SECTOR = "sector"
    CLAIM_TYPE = "claim_type"


class MemoryRecord(BaseModel):
    """
    Durable, isolated analytical lesson stored by an agent.
    """
    id: str = Field(..., description="Unique memory ID, e.g. MEM-LOKI-001")
    agent_id: str = Field(..., description="'heimdall', 'thor', 'loki', or 'odin'")
    memory_type: MemoryType
    content: str = Field(..., min_length=5, description="Concise, actionable lesson or strategic rule")
    scope: MemoryScope = Field(default=MemoryScope.GLOBAL)
    scope_value: Optional[str] = Field(default=None, description="e.g. 'E5' or 'Midgard' or 'agriculture'")
    basis_refs: List[str] = Field(default_factory=list, description="Claim, ruling, or doc IDs justifying this lesson")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_run: int = Field(default=1)
    last_used_run: Optional[int] = Field(default=None)
    status: str = Field(default="active", description="'active', 'superseded', or 'rejected'")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MemoryEvent(BaseModel):
    """
    Append-only audit trail proving memory changed agent behavior (Acceptance Check 9).
    """
    case_id: str
    run_no: int
    agent_id: str
    event_type: str = Field(..., description="'memory_written', 'memory_read', 'query_changed_by_memory', 'claim_revised'")
    memory_id: Optional[str] = None
    previous_query: Optional[str] = None
    new_query: Optional[str] = None
    previous_filters: Optional[Dict[str, Any]] = None
    new_filters: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


class MemoryQuery(BaseModel):
    """
    Query parameters for agent memory retrieval.
    """
    agent_id: str = Field(..., description="Calling agent ID (isolation enforced)")
    event_id: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    claim_type: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=10)
