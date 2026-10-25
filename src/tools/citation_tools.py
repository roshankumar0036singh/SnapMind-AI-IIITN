import re
from datetime import date
from typing import Optional, Dict, Any

from src.schemas.citations import CitationVerifyRequest, CitationVerifyResponse
from src.supabase_client import get_supabase_client, get_supabase_admin


class CitationValidator:
    """
    Automated validator for agent evidence citations.
    Resolves:
    1. DOC-ID (e.g. 'ATL-0001')
    2. DOC-ID#Pn (e.g. 'ATL-0001#P2')
    3. TABLE-ID#row (e.g. 'TRD-E5-01#04')
    Enforces Simulated Clock gates, retraction exclusions, damage traps, and prompt-injection quarantines.
    """

    DOC_REF_PATTERN = re.compile(r"^([A-Z0-9]+(?:-[A-Z0-9]+)+)(?:#P(\d+))?$", re.IGNORECASE)
    TABLE_REF_PATTERN = re.compile(r"^([A-Z0-9]+(?:-[A-Z0-9]+)+)#(\d+)(?:-\d+)?$", re.IGNORECASE)

    def __init__(self, local_docs: Optional[Dict[str, Dict[str, Any]]] = None, local_trade_rows: Optional[Dict[str, Dict[str, Any]]] = None):
        self._client = None
        self._admin = None
        # In-memory overrides for unit testing without live network calls
        self._local_docs = local_docs or {}
        self._local_trade_rows = local_trade_rows or {}

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @property
    def admin(self):
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    def register_local_doc(self, doc_id: str, doc_data: Dict[str, Any]):
        """Register local doc for offline testing."""
        self._local_docs[doc_id.upper()] = doc_data

    def register_local_trade_row(self, citation_key: str, row_data: Dict[str, Any]):
        """Register local trade row for offline testing."""
        self._local_trade_rows[citation_key.upper()] = row_data

    def verify_citation(
        self,
        citation_ref: str,
        case_as_of_date: date,
    ) -> CitationVerifyResponse:
        """
        Validates a citation reference against the simulated clock and data stores.
        """
        ref = citation_ref.strip()
        if not ref:
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason="empty_citation",
            )

        # 1. Check if citation is a trade table row (e.g., TRD-E5-01#04)
        if "#" in ref and ("TRD" in ref.upper() or "TAB" in ref.upper()):
            return self._verify_trade_citation(ref, case_as_of_date)

        # 2. Check if citation is a document or paragraph (e.g., ATL-0001, ORV-0005#P2)
        doc_match = self.DOC_REF_PATTERN.match(ref)
        if doc_match:
            doc_id = doc_match.group(1).upper()
            paragraph_no = int(doc_match.group(2)) if doc_match.group(2) else None
            return self._verify_document_citation(ref, doc_id, paragraph_no, case_as_of_date)

        # 3. Fallback: Try trade regex match
        table_match = self.TABLE_REF_PATTERN.match(ref)
        if table_match:
            return self._verify_trade_citation(ref, case_as_of_date)

        return CitationVerifyResponse(
            citation_ref=citation_ref,
            is_valid=False,
            reason="invalid_citation_format",
        )

    def _verify_document_citation(
        self,
        citation_ref: str,
        doc_id: str,
        paragraph_no: Optional[int],
        case_as_of_date: date,
    ) -> CitationVerifyResponse:
        """Verifies a document or paragraph reference."""
        doc_data = None

        # Check local cache first
        if doc_id in self._local_docs:
            doc_data = self._local_docs[doc_id]
        else:
            try:
                res = self.client.table("runemark_documents").select("*").eq("doc_id", doc_id).execute()
                if res.data and len(res.data) > 0:
                    doc_data = res.data[0]
            except Exception:
                pass

        if not doc_data:
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason="doc_not_found",
                doc_id=doc_id,
            )

        # Check simulated clock gate
        raw_pub_date = doc_data.get("pub_date")
        if isinstance(raw_pub_date, str):
            pub_date = date.fromisoformat(raw_pub_date)
        elif isinstance(raw_pub_date, date):
            pub_date = raw_pub_date
        else:
            pub_date = date(1970, 1, 1)

        if pub_date > case_as_of_date:
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason="post_as_of_violation",
                doc_id=doc_id,
                pub_date=pub_date,
                reliability_tier=doc_data.get("reliability_tier"),
            )

        # Check deliberate traps
        if doc_data.get("is_retracted"):
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason="retracted_source",
                doc_id=doc_id,
                pub_date=pub_date,
                reliability_tier=doc_data.get("reliability_tier"),
            )

        if doc_data.get("is_damaged"):
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason="damaged_source",
                doc_id=doc_id,
                pub_date=pub_date,
                reliability_tier=doc_data.get("reliability_tier"),
            )

        if doc_data.get("is_injection_attempt"):
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason="injection_quarantined",
                doc_id=doc_id,
                pub_date=pub_date,
                reliability_tier=doc_data.get("reliability_tier"),
            )

        # Extract excerpt (paragraph or body snippet)
        content = doc_data.get("content", "")
        excerpt = content
        if paragraph_no is not None:
            # Look for [Pn] paragraph tag
            tag = f"[P{paragraph_no}]"
            if tag in content:
                parts = content.split(tag)
                if len(parts) > 1:
                    next_part = parts[1]
                    # Cut off at next [P tag
                    next_tag_idx = re.search(r"\[P\d+\]", next_part)
                    if next_tag_idx:
                        excerpt = next_part[:next_tag_idx.start()].strip()
                    else:
                        excerpt = next_part.strip()
        if len(excerpt) > 300:
            excerpt = excerpt[:300] + "..."

        return CitationVerifyResponse(
            citation_ref=citation_ref,
            is_valid=True,
            reason="verified_ok",
            doc_id=doc_id,
            pub_date=pub_date,
            reliability_tier=doc_data.get("reliability_tier"),
            excerpt=excerpt,
            is_table_row=False,
        )

    def _verify_trade_citation(
        self,
        citation_ref: str,
        case_as_of_date: date,
    ) -> CitationVerifyResponse:
        """Verifies a trade table row citation (TABLE-ID#row)."""
        parts = citation_ref.split("#")
        table_id = parts[0].strip().upper()
        row_part = parts[1].strip() if len(parts) > 1 else "1"

        # If range, take first row
        first_row_no = int(row_part.split("-")[0].split(",")[0])

        lookup_keys = [
            f"{table_id}#{first_row_no}".upper(),
            f"{table_id}#{first_row_no:02d}".upper(),
            citation_ref.upper(),
        ]
        row_data = None
        for k in lookup_keys:
            if k in self._local_trade_rows:
                row_data = self._local_trade_rows[k]
                break

        if row_data is None:
            try:
                res = self.client.table("trade_rows").select("*").eq("table_id", table_id).eq("row_no", first_row_no).execute()
                if res.data and len(res.data) > 0:
                    row_data = res.data[0]
            except Exception:
                pass

        if not row_data:
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason="row_not_found",
                is_table_row=True,
                table_id=table_id,
                row_no=first_row_no,
            )

        raw_month = row_data.get("month")
        if isinstance(raw_month, str):
            month = date.fromisoformat(raw_month)
        elif isinstance(raw_month, date):
            month = raw_month
        else:
            month = date(1970, 1, 1)

        # Check clock gate
        if month > case_as_of_date:
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason="post_as_of_violation",
                is_table_row=True,
                table_id=table_id,
                row_no=first_row_no,
                pub_date=month,
            )

        # Check row hygiene
        row_status = row_data.get("row_status", "ok")
        if row_status != "ok":
            return CitationVerifyResponse(
                citation_ref=citation_ref,
                is_valid=False,
                reason=f"damaged_row_{row_status}",
                is_table_row=True,
                table_id=table_id,
                row_no=first_row_no,
                pub_date=month,
            )

        excerpt = (
            f"Table {table_id} Row {first_row_no} ({month}): "
            f"Volume={row_data.get('volume')}, Value={row_data.get('value')}"
        )

        return CitationVerifyResponse(
            citation_ref=citation_ref,
            is_valid=True,
            reason="verified_ok",
            is_table_row=True,
            table_id=table_id,
            row_no=first_row_no,
            pub_date=month,
            reliability_tier=1,  # Customs and trade rows are Tier 1 statistical records
            excerpt=excerpt,
        )


_citation_validator: Optional[CitationValidator] = None

def get_citation_validator() -> CitationValidator:
    global _citation_validator
    if _citation_validator is None:
        _citation_validator = CitationValidator()
    return _citation_validator
