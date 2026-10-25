from datetime import date, datetime
from typing import List, Tuple, Optional, Union, Dict, Any

from src.schemas.trade import TradeRow, TradeTableHeader, MetricCalculationResult
from src.trade.validator import TradeRowValidator
from src.supabase_client import get_supabase_client, get_supabase_admin


class TradeAnalyticsEngine:
    """
    Deterministic mathematical engine for calculating commercial trade volume and value changes.
    Enforces Simulated Clock gates, excludes corrupted rows with complete audit trails,
    and returns verifiable citations (TABLE-ID#row).
    """

    def __init__(self):
        self._client = None
        self._admin = None

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

    @staticmethod
    def _parse_window_boundary(val: Union[str, date], is_end: bool = False) -> date:
        """Parses a date or YYYY-MM string into a date object."""
        if isinstance(val, date):
            return val
        s = str(val).strip()
        dt = TradeRowValidator.parse_month(s)
        if dt:
            if is_end and len(s) <= 7:
                # If YYYY-MM, span to end of month (approximate to 28-31)
                import calendar
                last_day = calendar.monthrange(dt.year, dt.month)[1]
                return date(dt.year, dt.month, last_day)
            return dt
        raise ValueError(f"Invalid date format for window boundary: '{val}'")

    def fetch_rows(
        self,
        table_id: str,
        as_of_date: Optional[date] = None,
        in_memory_rows: Optional[List[TradeRow]] = None,
    ) -> List[TradeRow]:
        """
        Retrieves rows for table_id, either from in-memory records or from Supabase.
        """
        if in_memory_rows is not None:
            return in_memory_rows

        try:
            query = self.client.table("trade_rows").select("*").eq("table_id", table_id).order("row_no")
            res = query.execute()
            rows: List[TradeRow] = []
            for r in res.data:
                rows.append(TradeRow(
                    table_id=r["table_id"],
                    row_no=r["row_no"],
                    month=date.fromisoformat(r["month"]),
                    volume=float(r["volume"]) if r.get("volume") is not None else None,
                    value=float(r["value"]) if r.get("value") is not None else None,
                    row_status=r.get("row_status", "ok"),
                    flag_reason=r.get("flag_reason"),
                ))
            return rows
        except Exception:
            return []

    def compute_change(
        self,
        table_id: str,
        baseline_window: Tuple[Union[str, date], Union[str, date]],
        comparison_window: Tuple[Union[str, date], Union[str, date]],
        metric: str = "volume",
        as_of_date: Optional[date] = None,
        in_memory_rows: Optional[List[TradeRow]] = None,
    ) -> MetricCalculationResult:
        """
        Calculates baseline vs comparison averages, absolute change, and percentage change.
        """
        metric_norm = metric.lower().strip()
        if metric_norm not in {"volume", "value"}:
            raise ValueError(f"Metric must be 'volume' or 'value', got '{metric}'")

        base_start = self._parse_window_boundary(baseline_window[0], is_end=False)
        base_end = self._parse_window_boundary(baseline_window[1], is_end=True)
        comp_start = self._parse_window_boundary(comparison_window[0], is_end=False)
        comp_end = self._parse_window_boundary(comparison_window[1], is_end=True)

        all_rows = self.fetch_rows(table_id, as_of_date, in_memory_rows)
        if not all_rows:
            raise ValueError(f"No trade rows found for table '{table_id}'")

        base_values: List[float] = []
        comp_values: List[float] = []
        rows_used: List[int] = []
        rows_excluded: List[int] = []

        for row in all_rows:
            r_month = row.month
            r_val = row.volume if metric_norm == "volume" else row.value

            # Check if row is in either window
            in_base = base_start <= r_month <= base_end
            in_comp = comp_start <= r_month <= comp_end

            if not in_base and not in_comp:
                continue

            # Check clock gate
            if as_of_date and r_month > as_of_date:
                rows_excluded.append(row.row_no)
                continue

            # Check row status hygiene
            if row.row_status != "ok" or r_val is None:
                rows_excluded.append(row.row_no)
                continue

            # Row is valid and in window
            rows_used.append(row.row_no)
            if in_base:
                base_values.append(r_val)
            if in_comp:
                comp_values.append(r_val)

        if not base_values:
            raise ValueError(
                f"No valid baseline rows found in window {base_start} to {base_end} for table '{table_id}' "
                f"(excluded rows: {rows_excluded})"
            )
        if not comp_values:
            raise ValueError(
                f"No valid comparison rows found in window {comp_start} to {comp_end} for table '{table_id}' "
                f"(excluded rows: {rows_excluded})"
            )

        base_avg = round(sum(base_values) / len(base_values), 2)
        comp_avg = round(sum(comp_values) / len(comp_values), 2)

        abs_diff = round(comp_avg - base_avg, 2)
        if base_avg == 0:
            pct_change = 0.0
        else:
            pct_change = round(((comp_avg - base_avg) / base_avg) * 100.0, 2)

        # Generate canonical citation ref
        rows_used_sorted = sorted(set(rows_used))
        if len(rows_used_sorted) > 1 and rows_used_sorted[-1] - rows_used_sorted[0] == len(rows_used_sorted) - 1:
            citation_ref = f"{table_id}#{rows_used_sorted[0]}-{rows_used_sorted[-1]}"
        else:
            citation_ref = f"{table_id}#" + ",".join(str(r) for r in rows_used_sorted)

        direction = "drop" if pct_change < 0 else "increase"
        explanation = (
            f"Calculated {direction} of {abs(pct_change)}% in {metric_norm} "
            f"(baseline: {base_avg}, comparison: {comp_avg}, net diff: {abs_diff}). "
            f"Evaluated {len(rows_used)} clean rows ({len(rows_excluded)} excluded for damage/clock)."
        )

        return MetricCalculationResult(
            table_id=table_id,
            metric=metric_norm,
            baseline_window=f"{base_start} to {base_end}",
            baseline_average=base_avg,
            comparison_window=f"{comp_start} to {comp_end}",
            comparison_average=comp_avg,
            percentage_change=pct_change,
            absolute_change=abs_diff,
            rows_used=rows_used_sorted,
            rows_excluded=sorted(set(rows_excluded)),
            explanation=explanation,
            citation_ref=citation_ref,
        )


_trade_engine: Optional[TradeAnalyticsEngine] = None

def get_trade_engine() -> TradeAnalyticsEngine:
    global _trade_engine
    if _trade_engine is None:
        _trade_engine = TradeAnalyticsEngine()
    return _trade_engine
