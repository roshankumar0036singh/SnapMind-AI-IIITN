from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class CitationVerifyRequest(BaseModel):
    """
    Request to verify an agent's evidence citation reference.
    """
    citation_ref: str = Field(..., description="Reference ID: DOC-ID, DOC-ID#Pn, or TABLE-ID#row")
    case_as_of_date: date = Field(..., description="Simulated Clock date for the active case")


class CitationVerifyResponse(BaseModel):
    """
    Validation output for citation auditing and judicial review.
    """
    citation_ref: str
    is_valid: bool = Field(..., description="True only if exists in manifest, within clock, and not retracted")
    reason: str = Field(..., description="'verified_ok', 'doc_not_found', 'post_as_of_violation', 'retracted_source', 'damaged_source', 'injection_quarantined'")
    doc_id: Optional[str] = None
    pub_date: Optional[date] = None
    reliability_tier: Optional[int] = None
    excerpt: Optional[str] = None
    is_table_row: bool = False
    table_id: Optional[str] = None
    row_no: Optional[int] = None
