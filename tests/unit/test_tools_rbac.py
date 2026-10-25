from datetime import date
import pytest

from src.tools.registry import AgentToolRegistry
from src.tools.citation_tools import CitationValidator
from src.schemas.trade import TradeRow


def test_agent_tool_registry_rbac_permissions():
    registry = AgentToolRegistry()

    # Thor and Loki can search and compute change
    assert registry.is_tool_allowed("thor", "search_docs") is True
    assert registry.is_tool_allowed("thor", "compute_change") is True
    assert registry.is_tool_allowed("loki", "search_docs") is True
    assert registry.is_tool_allowed("loki", "compute_change") is True

    # Heimdall can search docs but not compute trade change
    assert registry.is_tool_allowed("heimdall", "search_docs") is True
    assert registry.is_tool_allowed("heimdall", "compute_change") is False

    # Odin CANNOT search docs or compute change
    assert registry.is_tool_allowed("odin", "search_docs") is False
    assert registry.is_tool_allowed("odin", "compute_change") is False
    assert registry.is_tool_allowed("odin", "find_tables") is False

    # Odin CAN verify citations and get docs
    assert registry.is_tool_allowed("odin", "verify_citation") is True
    assert registry.is_tool_allowed("odin", "get_doc") is True


def test_odin_prohibited_tools_raise_permission_error():
    registry = AgentToolRegistry()

    # Odin attempting to call search_docs must raise PermissionError
    with pytest.raises(PermissionError, match="strictly prohibited"):
        registry.execute_tool("odin", "search_docs", query_text="grain price collapse")

    # Odin attempting to call compute_change must raise PermissionError
    with pytest.raises(PermissionError, match="strictly prohibited"):
        registry.execute_tool("odin", "compute_change", table_id="TRD-01")


def test_citation_validator_document_checks():
    validator = CitationValidator()

    # Register local mock documents
    validator.register_local_doc("ORV-0005", {
        "doc_id": "ORV-0005",
        "title": "Orvan Harvest Bulletin",
        "content": "[P1] Harvest completed with standard yields. [P2] Export corridors remain open at nominal capacity.",
        "pub_date": "2026-10-15",
        "reliability_tier": 1,
        "is_retracted": False,
        "is_damaged": False,
        "is_injection_attempt": False,
    })

    validator.register_local_doc("ORV-0099", {
        "doc_id": "ORV-0099",
        "title": "Future Leaked Report",
        "content": "[P1] Post-event secret report.",
        "pub_date": "2027-02-10",  # After as_of_date (2027-01-25)
        "reliability_tier": 2,
        "is_retracted": False,
        "is_damaged": False,
        "is_injection_attempt": False,
    })

    validator.register_local_doc("ORV-0088", {
        "doc_id": "ORV-0088",
        "title": "False Rumour",
        "content": "Corridor collapsed completely.",
        "pub_date": "2026-09-01",
        "reliability_tier": 4,
        "is_retracted": True,  # Retracted trap
        "is_damaged": False,
        "is_injection_attempt": False,
    })

    as_of = date(2027, 1, 25)

    # 1. Valid full document
    res_full = validator.verify_citation("ORV-0005", as_of)
    assert res_full.is_valid is True
    assert res_full.reason == "verified_ok"
    assert res_full.reliability_tier == 1

    # 2. Valid paragraph chunk
    res_p2 = validator.verify_citation("ORV-0005#P2", as_of)
    assert res_p2.is_valid is True
    assert res_p2.reason == "verified_ok"
    assert "Export corridors remain open" in res_p2.excerpt

    # 3. Post-as-of clock violation
    res_future = validator.verify_citation("ORV-0099", as_of)
    assert res_future.is_valid is False
    assert res_future.reason == "post_as_of_violation"

    # 4. Retracted document trap
    res_retracted = validator.verify_citation("ORV-0088", as_of)
    assert res_retracted.is_valid is False
    assert res_retracted.reason == "retracted_source"

    # 5. Non-existent document
    res_missing = validator.verify_citation("NONEXISTENT-9999", as_of)
    assert res_missing.is_valid is False
    assert res_missing.reason == "doc_not_found"


def test_citation_validator_trade_row_checks():
    validator = CitationValidator()

    # Register local mock trade rows
    validator.register_local_trade_row("TRD-E5-01#04", {
        "table_id": "TRD-E5-01",
        "row_no": 4,
        "month": "2026-04-01",
        "volume": 105.0,
        "value": 31.5,
        "row_status": "ok",
    })

    validator.register_local_trade_row("TRD-E5-01#15", {
        "table_id": "TRD-E5-01",
        "row_no": 15,
        "month": "2027-03-01",  # Future month
        "volume": 60.0,
        "value": 20.0,
        "row_status": "ok",
    })

    validator.register_local_trade_row("TRD-E5-01#08", {
        "table_id": "TRD-E5-01",
        "row_no": 8,
        "month": "2026-08-01",
        "volume": None,
        "value": None,
        "row_status": "missing",  # Damaged row trap
    })

    as_of = date(2027, 1, 25)

    # Valid trade row
    res_trd_ok = validator.verify_citation("TRD-E5-01#04", as_of)
    assert res_trd_ok.is_valid is True
    assert res_trd_ok.is_table_row is True
    assert res_trd_ok.reason == "verified_ok"
    assert "Volume=105.0" in res_trd_ok.excerpt

    # Future trade row clock violation
    res_trd_future = validator.verify_citation("TRD-E5-01#15", as_of)
    assert res_trd_future.is_valid is False
    assert res_trd_future.reason == "post_as_of_violation"

    # Damaged trade row trap
    res_trd_damaged = validator.verify_citation("TRD-E5-01#08", as_of)
    assert res_trd_damaged.is_valid is False
    assert res_trd_damaged.reason == "damaged_row_missing"
