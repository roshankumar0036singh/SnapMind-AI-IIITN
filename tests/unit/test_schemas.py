from datetime import date
import pytest
from pydantic import ValidationError

from src.schemas import (
    DocumentMetadata,
    DocumentDamageReport,
    ParagraphChunk,
    IngestReport,
    SearchFilters,
    SearchQuery,
    SearchResultItem,
    SearchResponse,
    TradeTableHeader,
    TradeRow,
    MetricCalculationResult,
    CitationVerifyRequest,
    CitationVerifyResponse,
    MemoryType,
    MemoryScope,
    MemoryRecord,
    MemoryEvent,
    ClaimKind,
    Claim,
    Attack,
    Defence,
    RulingOutcome,
    RulingBasis,
    Ruling,
    ClassificationSummary,
    CountrySectorRange,
    CaseStatus,
    EventScope,
    VerificationVerdict,
    RunRecord,
    CaseFile,
)


def test_document_metadata_valid():
    doc = DocumentMetadata(
        doc_id="ATL-0002",
        event_id="NONE",
        title="Country profile: Asgard",
        source_name="Realm Trade Ministry",
        source_type="atlas",
        reliability_tier=1,
        pub_date=date(2024, 1, 15),
        pub_time="09:00",
        country="Asgard",
        sector="general",
        language="en",
        file_name="ATL-0002.txt",
        format="txt",
    )
    assert doc.doc_id == "ATL-0002"
    assert doc.reliability_tier == 1
    assert doc.format == "TXT"  # Uppercased by validator


def test_document_metadata_invalid_tier():
    with pytest.raises(ValidationError):
        DocumentMetadata(
            doc_id="BAD-0001",
            title="Bad Tier",
            source_name="Outlet",
            source_type="blog",
            reliability_tier=5,  # Must be 1 to 4
            pub_date=date(2026, 1, 1),
            country="Midgard",
            sector="general",
        )


def test_paragraph_chunk():
    doc = DocumentMetadata(
        doc_id="ORV-0005",
        title="Grain Corridor",
        source_name="Port Bulletin",
        source_type="official",
        reliability_tier=1,
        pub_date=date(2027, 1, 18),
        country="Orvan",
        sector="agriculture",
    )
    chunk = ParagraphChunk(
        chunk_id="ORV-0005#P2",
        doc_id="ORV-0005",
        paragraph_no=2,
        text="Warehouse stockpiles stand at 140,000 metric tons.",
        metadata=doc,
    )
    assert chunk.chunk_id == "ORV-0005#P2"
    assert chunk.paragraph_no == 2
    assert chunk.embedding is None


def test_search_filters_and_query():
    filters = SearchFilters(
        as_of_date=date(2027, 1, 25),
        country="Midgard",
        sector="agriculture",
        tier_max=2,
    )
    query = SearchQuery(
        agent_id="thor",
        query_text="grain export stoppage Midgard",
        filters=filters,
        top_k=5,
    )
    assert query.agent_id == "thor"
    assert query.filters.as_of_date == date(2027, 1, 25)
    assert query.filters.exclude_retracted is True


def test_trade_row_citation_property():
    row = TradeRow(
        table_id="TAB-E5-01",
        row_no=12,
        month=date(2026, 12, 1),
        volume=120.5,
        value=45.2,
        row_status="ok",
    )
    assert row.citation_ref == "TAB-E5-01#12"


def test_memory_record_and_event():
    mem = MemoryRecord(
        id="MEM-LOKI-001",
        agent_id="loki",
        memory_type=MemoryType.SOURCE_LESSON,
        content="Do not rely on Tier 4 sources for supply claims without Tier 1/2 corroboration.",
        scope=MemoryScope.CLAIM_TYPE,
        basis_refs=["CLM-LOKI-R1-02", "RUL-ODIN-02"],
        confidence=0.9,
    )
    assert mem.agent_id == "loki"
    assert mem.memory_type == MemoryType.SOURCE_LESSON

    event = MemoryEvent(
        case_id="case_E5_001",
        run_no=2,
        agent_id="loki",
        event_type="query_changed_by_memory",
        memory_id=mem.id,
        previous_query="grain buffer stocks",
        new_query="grain buffer stocks official wire",
        reason="Tier 4 source rejected in run 1; added tier_max: 2",
    )
    assert event.event_type == "query_changed_by_memory"


def test_claim_attack_ruling_flow():
    claim = Claim(
        claim_id="CLM-THOR-R1-01",
        agent="thor",
        run_no=1,
        round_no=1,
        text="Midgard wheat imports will drop by 45% due to corridor closure.",
        country="Midgard",
        sector="wheat",
        estimate_low=-40.0,
        estimate_high=-50.0,
        kind=ClaimKind.CALCULATION,
        citations=["ORV-0005#P2", "TAB-E5-01#12"],
    )
    assert claim.kind == ClaimKind.CALCULATION

    attack = Attack(
        attack_id="ATK-LOKI-R2-01",
        from_agent="loki",
        target_claim_id=claim.claim_id,
        grounds="bad_method",
        evidence_refs=["ORV-0041#P6"],
        text="Thor uses deepest single month rather than average post-event volume.",
    )
    assert attack.target_claim_id == "CLM-THOR-R1-01"

    ruling = Ruling(
        ruling_id="RUL-ODIN-01",
        claim_id=claim.claim_id,
        outcome=RulingOutcome.CONTESTED,
        basis=RulingBasis.CALCULATION,
        reasoning="Method uses a trough month; alternative rail volumes partially offset decline.",
        refs_checked=["ORV-0005#P2", "TAB-E5-01#12", "ORV-0041#P6"],
    )
    assert ruling.outcome == RulingOutcome.CONTESTED


def test_case_file_serialization():
    cf = CaseFile(
        case_id="case_E5_test",
        question="How exposed are Midgard and Tolan to the Orvan corridor collapse?",
        as_of=date(2027, 1, 25),
        status=CaseStatus.OPEN,
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Midgard", "Tolan"],
            target_sectors=["wheat", "maize"],
            as_of_date=date(2027, 1, 25),
        ),
        verification=VerificationVerdict(
            verdict="real",
            confidence=1.0,
            reasons=["Confirmed by Tier 1 Regional Port Authority notice"],
            supporting_docs=["ORV-0005"],
            message_to_user="Event confirmed real and active.",
        ),
    )
    json_str = cf.model_dump_json()
    assert "case_E5_test" in json_str
    assert "Orvan grain corridor collapse" in json_str

    deserialized = CaseFile.model_validate_json(json_str)
    assert deserialized.scope.event_id == "E5"
    assert deserialized.verification.verdict == "real"
