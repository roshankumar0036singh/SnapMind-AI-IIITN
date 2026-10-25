from typing import List, Dict, Any, Optional
from src.supabase_client import get_supabase_admin

class TradeTools:
    """
    Handles structured Trade Table queries and calculations in Supabase (Section 9):
    1. find_tables: Locates trade tables for given country, sector, or event.
    2. get_table: Fetches metadata and valid rows.
    3. compute_change: Computes pre-event baseline average vs post-event drop %,
       strictly filtering rows beyond the as_of_date and excluding flagged/bad rows.
    """
    def __init__(self):
        self.supabase = get_supabase_admin()

    def find_tables(
        self,
        country: Optional[str] = None,
        sector: Optional[str] = None,
        event_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find matching trade tables in Supabase."""
        try:
            query = self.supabase.table("trade_tables").select("*")
            if country:
                query = query.ilike("country_pair", f"%{country}%")
            if sector:
                query = query.ilike("sector", f"%{sector}%")
            if event_id:
                query = query.eq("event_id", event_id)
            res = query.execute()
            return res.data or []
        except Exception as e:
            print(f"[TradeTools] find_tables failed: {e}")
            return []

    def get_table(self, table_id: str, as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """Fetch table metadata and rows filtered by as_of_date."""
        try:
            table_meta = self.supabase.table("trade_tables") \
                .select("*") \
                .eq("table_id", table_id) \
                .single() \
                .execute().data

            row_query = self.supabase.table("trade_rows") \
                .select("*") \
                .eq("table_id", table_id) \
                .order("row_no")
            
            if as_of_date:
                row_query = row_query.lte("month", as_of_date)

            rows = row_query.execute().data or []
            return {"table": table_meta, "rows": rows}
        except Exception as e:
            print(f"[TradeTools] get_table failed for {table_id}: {e}")
            return {"table": None, "rows": []}

    def compute_change(
        self,
        table_id: str,
        baseline_start: str,
        baseline_end: str,
        comparison_start: str,
        comparison_end: str,
        as_of_date: str,
        metric: str = "volume"  # 'volume' or 'value'
    ) -> Dict[str, Any]:
        """
        Computes percentage change between baseline window and comparison window.
        Returns exact rows used and excluded for citation verification.
        """
        try:
            # Fetch all rows up to as_of_date
            res = self.supabase.table("trade_rows") \
                .select("*") \
                .eq("table_id", table_id) \
                .lte("month", as_of_date) \
                .execute()
            
            rows = res.data or []
            if not rows:
                return {"error": f"No data found for table {table_id} within as-of date {as_of_date}"}

            baseline_vals = []
            baseline_rows_used = []
            comp_vals = []
            comp_rows_used = []
            rows_excluded = []

            for r in rows:
                # Strictly check row status - only 'ok' rows feed calculations
                if r.get("row_status") != "ok":
                    rows_excluded.append(r["row_no"])
                    continue

                month = str(r["month"])
                val = r.get(metric)
                if val is None:
                    rows_excluded.append(r["row_no"])
                    continue

                val = float(val)

                if baseline_start <= month <= baseline_end:
                    baseline_vals.append(val)
                    baseline_rows_used.append(r["row_no"])
                elif comparison_start <= month <= comparison_end:
                    comp_vals.append(val)
                    comp_rows_used.append(r["row_no"])

            if not baseline_vals or not comp_vals:
                return {
                    "error": "Insufficient valid rows in baseline or comparison window",
                    "rows_excluded": rows_excluded
                }

            baseline_avg = sum(baseline_vals) / len(baseline_vals)
            comp_avg = sum(comp_vals) / len(comp_vals)

            if baseline_avg == 0:
                pct_change = 0.0
            else:
                pct_change = ((comp_avg - baseline_avg) / baseline_avg) * 100.0

            # Generate row citation string e.g. TABLE-ID#row
            cited_rows = [f"{table_id}#{r}" for r in comp_rows_used]

            return {
                "table_id": table_id,
                "metric": metric,
                "baseline_average": round(baseline_avg, 2),
                "comparison_average": round(comp_avg, 2),
                "percentage_change": round(pct_change, 2),
                "baseline_rows_used": baseline_rows_used,
                "comparison_rows_used": comp_rows_used,
                "rows_excluded": rows_excluded,
                "citations": cited_rows
            }
        except Exception as e:
            print(f"[TradeTools] compute_change failed: {e}")
            return {"error": str(e)}
