import pytest
from src.tools.registry import AgentToolRegistry
from src.tools import odin_tools


def test_odin_rbac_prohibited_tools_in_registry():
    registry = AgentToolRegistry()
    assert not registry.is_tool_allowed("odin", "search_docs")
    assert not registry.is_tool_allowed("odin", "find_tables")
    assert not registry.is_tool_allowed("odin", "compute_change")

    with pytest.raises(PermissionError) as exc_info:
        registry.execute_tool("odin", "search_docs", query="wheat disruption")
    assert "strictly prohibited" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        registry.execute_tool("odin", "find_tables", country="Nordland")
    assert "strictly prohibited" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        registry.execute_tool("odin", "compute_change", table_id="TRD-E5-01")
    assert "strictly prohibited" in str(exc_info.value)


def test_odin_tools_module_direct_prohibitions():
    with pytest.raises(PermissionError) as exc_info:
        odin_tools.search_docs("wheat")
    assert "strictly prohibited from executing 'search_docs'" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        odin_tools.find_tables()
    assert "strictly prohibited from executing 'find_tables'" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        odin_tools.compute_change()
    assert "strictly prohibited from executing 'compute_change'" in str(exc_info.value)


def test_odin_allowed_tools_in_registry():
    registry = AgentToolRegistry()
    allowed = registry.get_allowed_tools("odin")
    expected = {
        "get_doc",
        "verify_citation",
        "read_case_file",
        "post_to_case_file",
        "read_memory",
        "write_memory",
    }
    assert allowed == expected


def test_odin_case_file_post_whitelisting():
    # Attempting to post to an unwhitelisted section should raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        odin_tools.post_to_case_file(case_id="CASE-01", section="unauthorized_section", payload={})
    assert "not permitted to write" in str(exc_info.value)
