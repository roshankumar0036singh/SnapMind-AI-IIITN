from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class DocumentMetadata(BaseModel):
    """
    Standard 11-field metadata header found in all Runemark documents.
    """
    doc_id: str = Field(..., description="Permanent ID, e.g. ATL-0001, ORV-0005")
    event_id: str = Field(default="NONE", description="Associated event ID, e.g. E5 or NONE for background")
    title: str = Field(..., description="Document headline or title")
    source_name: str = Field(..., description="Publishing outlet name, e.g. Realm Trade Ministry, Raven Wire")
    source_type: str = Field(..., description="Category: atlas, wire, official, trade, regional, blog")
    reliability_tier: int = Field(..., ge=1, le=4, description="Credibility tier: 1 (Official), 2 (Wire/Daily), 3 (Regional), 4 (Blog/Social)")
    pub_date: date = Field(..., description="Publication date YYYY-MM-DD")
    pub_time: Optional[str] = Field(default=None, description="Publication time HH:MM")
    country: str = Field(..., description="Target nation or general")
    sector: str = Field(..., description="Target economic sector or general")
    language: str = Field(default="en", description="Document language code")
    file_name: Optional[str] = Field(default=None, description="Original filename with extension")
    format: str = Field(default="TXT", description="Format: PDF, TXT, or DOCX")

    @field_validator("format")
    @classmethod
    def normalize_format(cls, v: str) -> str:
        return v.upper()


class DocumentDamageReport(BaseModel):
    """
    Integrity and adversarial trap scan results for a document.
    """
    is_damaged: bool = Field(default=False, description="True if empty, truncated, or unreadable encoding")
    damage_type: Optional[str] = Field(default=None, description="'empty', 'truncated', or 'encoding'")
    is_duplicate: bool = Field(default=False, description="True if exact or near-duplicate of an existing document")
    duplicate_of: Optional[str] = Field(default=None, description="Canonical doc_id if this is a duplicate")
    is_retracted: bool = Field(default=False, description="True if an official notice retracted this article")
    retracted_by: Optional[str] = Field(default=None, description="Doc ID of retraction notice")
    is_corrected: bool = Field(default=False, description="True if a correction was published")
    corrected_by: Optional[str] = Field(default=None, description="Doc ID of correction article")
    is_injection_attempt: bool = Field(default=False, description="True if prompt override instructions detected")
    injection_spans: List[str] = Field(default_factory=list, description="Suspicious text excerpts detected")
    quarantine_reason: Optional[str] = Field(default=None, description="Explanation if excluded from retrieval")


class ParagraphChunk(BaseModel):
    """
    Structure-aware chunk tied to exact Runemark paragraph tags ([P1], [P2], etc.).
    """
    chunk_id: str = Field(..., description="Deterministic citation ID: DOC_ID#Pn, e.g. ORV-0005#P2")
    doc_id: str = Field(..., description="Parent document ID")
    paragraph_no: int = Field(..., ge=1, description="1-indexed paragraph number")
    text: str = Field(..., min_length=1, description="Paragraph body text")
    metadata: DocumentMetadata
    damage_report: DocumentDamageReport = Field(default_factory=DocumentDamageReport)
    embedding: Optional[List[float]] = Field(default=None, description="768-dim vector from Gemini gemini-embedding-2")


class IngestReport(BaseModel):
    """
    Summary of an ingestion run (dev pack or live final round pack).
    """
    pack_name: str
    event_id: str
    as_of: date
    total_files: int
    files_ok: int
    files_damaged: List[Dict[str, Any]] = Field(default_factory=list)
    files_duplicated: List[Dict[str, Any]] = Field(default_factory=list)
    files_injection_flagged: List[Dict[str, Any]] = Field(default_factory=list)
