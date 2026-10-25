from typing import Dict, Set, Callable, Any, Optional, List
from datetime import date

from src.retrieval.hybrid_searcher import get_hybrid_searcher
from src.trade.analytics import get_trade_engine
from src.tools.citation_tools import get_citation_validator
from src.memory.manager import get_memory_manager
from src.schemas.retrieval import SearchQuery, SearchFilters, SearchResponse
from src.schemas.trade import MetricCalculationResult
from src.schemas.citations import CitationVerifyResponse


class AgentToolRegistry:
    """
    Role-Based Tool Registry enforcing strict agent permissions.
    Guarantee: Odin can NEVER search or compute trade math (NFR1 planner-free constraint).
    """

    ALLOWED_TOOLS: Dict[str, Set[str]] = {
        "heimdall": {
            "search_docs",
            "get_doc",
            "find_tables",
            "get_table",
            "read_case_file",
            "post_to_case_file",
            "read_memory",
            "write_memory",
        },
        "thor": {
            "search_docs",
            "get_doc",
            "find_tables",
            "get_table",
            "compute_change",
            "read_case_file",
            "post_to_case_file",
            "read_memory",
            "write_memory",
        },
        "loki": {
            "search_docs",
            "get_doc",
            "find_tables",
            "get_table",
            "compute_change",
            "read_case_file",
            "post_to_case_file",
            "read_memory",
            "write_memory",
        },
        "odin": {
            "get_doc",
            "verify_citation",
            "read_case_file",
            "post_to_case_file",
            "read_memory",
            "write_memory",
        },
    }

    # Tools that are explicitly forbidden for Odin
    ODIN_PROHIBITED_TOOLS: Set[str] = {"search_docs", "find_tables", "compute_change"}

    def __init__(self):
        self.searcher = get_hybrid_searcher()
        self.trade_engine = get_trade_engine()
        self.citation_validator = get_citation_validator()
        self.memory_manager = get_memory_manager()

    def is_tool_allowed(self, agent_id: str, tool_name: str) -> bool:
        """Checks if a tool is permitted for the given agent."""
        agent_norm = agent_id.lower().strip()
        allowed = self.ALLOWED_TOOLS.get(agent_norm, set())
        return tool_name in allowed

    def get_allowed_tools(self, agent_id: str) -> Set[str]:
        """Returns the set of tool names allowed for an agent."""
        agent_norm = agent_id.lower().strip()
        return self.ALLOWED_TOOLS.get(agent_norm, set()).copy()

    def execute_tool(self, agent_id: str, tool_name: str, **kwargs) -> Any:
        """
        Executes a tool on behalf of an agent after verifying RBAC permissions.
        """
        agent_norm = agent_id.lower().strip()

        # Hard gate check for Odin
        if agent_norm == "odin" and tool_name in self.ODIN_PROHIBITED_TOOLS:
            raise PermissionError(
                f"Judicial agent 'odin' is strictly prohibited from executing '{tool_name}' "
                f"(NFR1 constraint: Odin evaluates evidence only, never searches or computes)."
            )

        if not self.is_tool_allowed(agent_norm, tool_name):
            raise PermissionError(
                f"Agent '{agent_norm}' does not have permission to execute tool '{tool_name}'."
            )

        # Dispatch to underlying implementation
        if tool_name == "search_docs":
            return self._exec_search_docs(agent_norm, **kwargs)
        elif tool_name == "compute_change":
            return self._exec_compute_change(**kwargs)
        elif tool_name == "verify_citation":
            return self._exec_verify_citation(**kwargs)
        elif tool_name == "read_memory":
            return self._exec_read_memory(agent_norm, **kwargs)
        elif tool_name == "write_memory":
            return self._exec_write_memory(agent_norm, **kwargs)
        elif tool_name == "get_doc":
            return self._exec_get_doc(**kwargs)
        elif tool_name == "find_tables":
            return self._exec_find_tables(**kwargs)
        elif tool_name == "get_table":
            return self._exec_get_table(**kwargs)
        else:
            raise NotImplementedError(f"Tool handler for '{tool_name}' is not registered.")

    def _exec_search_docs(self, agent_id: str, **kwargs) -> SearchResponse:
        query_text = kwargs.get("query_text", "")
        filters = kwargs.get("filters")
        if isinstance(filters, dict):
            filters = SearchFilters(**filters)
        elif filters is None:
            filters = SearchFilters(as_of_date=kwargs.get("as_of_date", date.today()))
        top_k = kwargs.get("top_k", 5)

        query = SearchQuery(
            agent_id=agent_id,
            query_text=query_text,
            filters=filters,
            top_k=top_k,
        )
        return self.searcher.search(query)

    def _exec_compute_change(self, **kwargs) -> MetricCalculationResult:
        table_id = kwargs.get("table_id")
        baseline_window = kwargs.get("baseline_window")
        comparison_window = kwargs.get("comparison_window")
        metric = kwargs.get("metric", "volume")
        as_of_date_val = kwargs.get("as_of_date")
        in_memory_rows = kwargs.get("in_memory_rows")

        return self.trade_engine.compute_change(
            table_id=table_id,
            baseline_window=baseline_window,
            comparison_window=comparison_window,
            metric=metric,
            as_of_date=as_of_date_val,
            in_memory_rows=in_memory_rows,
        )

    def _exec_verify_citation(self, **kwargs) -> CitationVerifyResponse:
        citation_ref = kwargs.get("citation_ref")
        case_as_of_date = kwargs.get("case_as_of_date") or kwargs.get("as_of_date")
        if isinstance(case_as_of_date, str):
            case_as_of_date = date.fromisoformat(case_as_of_date)
        return self.citation_validator.verify_citation(citation_ref, case_as_of_date)

    def _exec_read_memory(self, agent_id: str, **kwargs) -> List[Any]:
        from src.schemas.memory import MemoryQuery
        query = MemoryQuery(
            agent_id=agent_id,
            event_id=kwargs.get("event_id"),
            country=kwargs.get("country"),
            sector=kwargs.get("sector"),
            limit=kwargs.get("limit", 5),
        )
        return self.memory_manager.retrieve_relevant_memories(query)

    def _exec_write_memory(self, agent_id: str, **kwargs) -> Optional[Any]:
        return self.memory_manager.write_memory(
            agent_id=agent_id,
            memory_type=kwargs.get("memory_type"),
            content=kwargs.get("content", ""),
            scope=kwargs.get("scope", "global"),
            scope_value=kwargs.get("scope_value") or kwargs.get("scope_key"),
            basis_refs=kwargs.get("basis_refs", []),
            confidence=kwargs.get("confidence", 1.0),
            run_no=kwargs.get("run_no", 1),
        )

    def _exec_get_doc(self, **kwargs) -> Optional[Dict[str, Any]]:
        doc_id = kwargs.get("doc_id", "").upper()
        res = self.searcher.client.table("runemark_documents").select("*").eq("doc_id", doc_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None

    def _exec_find_tables(self, **kwargs) -> List[Dict[str, Any]]:
        query = self.trade_engine.client.table("trade_tables").select("*")
        if kwargs.get("sector"):
            query = query.eq("sector", kwargs["sector"])
        if kwargs.get("country_pair"):
            query = query.eq("country_pair", kwargs["country_pair"])
        res = query.execute()
        return res.data or []

    def _exec_get_table(self, **kwargs) -> List[Dict[str, Any]]:
        table_id = kwargs.get("table_id")
        res = self.trade_engine.client.table("trade_rows").select("*").eq("table_id", table_id).order("row_no").execute()
        return res.data or []


_tool_registry: Optional[AgentToolRegistry] = None

def get_tool_registry() -> AgentToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = AgentToolRegistry()
    return _tool_registry
