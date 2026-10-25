from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """
    Hard metadata constraints applied to retrieval.
    Enforces Simulated Clock and trap exclusions.
    """
    as_of_date: date = Field(..., description="Simulated Clock cutoff: documents dated after this are strictly excluded")
    event_id: Optional[str] = Field(default=None, description="Event scope filter (e.g. 'E5')")
    country: Optional[str] = Field(default=None, description="Country filter (e.g. 'Midgard', 'Tolan')")
    sector: Optional[str] = Field(default=None, description="Sector filter (e.g. 'agriculture', 'shipping')")
    tier_max: Optional[int] = Field(default=4, ge=1, le=4, description="Maximum allowed credibility tier (1 to 4)")
    exclude_retracted: bool = Field(default=True, description="Strictly exclude retracted documents")
    exclude_damaged: bool = Field(default=True, description="Exclude damaged / unreadable documents")
    exclude_injections: bool = Field(default=True, description="Exclude documents with detected prompt injections")


class SearchQuery(BaseModel):
    """
    Search request issued by an authorized agent.
    """
    agent_id: str = Field(..., description="Calling agent: 'heimdall', 'thor', or 'loki'")
    query_text: str = Field(..., min_length=2, description="Keywords or natural language search string")
    filters: SearchFilters
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    use_reranker: bool = Field(default=False, description="Whether to apply secondary cross-encoder reranking")


class SearchResultItem(BaseModel):
    """
    Grounded excerpt returned from hybrid search.
    """
    chunk_id: str = Field(..., description="Exact paragraph ID, e.g. ORV-0005#P2")
    doc_id: str = Field(..., description="Parent document ID")
    paragraph_no: int = Field(default=1, description="Paragraph index")
    text: str = Field(..., description="Verified document excerpt")
    title: str = Field(..., description="Document headline")
    country: str
    sector: str
    pub_date: date
    reliability_tier: int = Field(..., ge=1, le=4)
    source_name: str
    source_type: str
    score: float = Field(..., description="Combined Reciprocal Rank Fusion (RRF) score")
    is_corrected: bool = Field(default=False)
    corrected_by: Optional[str] = Field(default=None)
    is_retracted: bool = Field(default=False)


class SearchResponse(BaseModel):
    """
    Full response bundle with deduplication and provenance metadata.
    """
    query_hash: str = Field(..., description="SHA256 hash of normalized query + filters")
    from_cache: bool = Field(default=False, description="True if served from query deduplication cache")
    total_candidates: int = Field(default=0)
    results: List[SearchResultItem] = Field(default_factory=list)
