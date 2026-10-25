import re
from datetime import date, datetime
from typing import Optional, Tuple, Any, Dict, Set
from src.schemas.trade import TradeRow


class TradeRowValidator:
    """
    Validates granular trade table rows and detects adversarial/damaged row traps:
    - 'missing': Empty, blank, or placeholder values (N/A, -, null)
    - 'bad_number': Non-numeric characters, formatting errors, or negative values
    - 'repeated': Duplicate month or duplicate row_no within the same table
    - 'cut_off': Incomplete rows missing columns
    - 'ok': Clean, valid numeric row
    """

    MISSING_MARKERS: Set[str] = {"", "n/a", "na", "null", "-", "none", "?", "missing"}

    def __init__(self):
        self.seen_months: Set[str] = set()
        self.seen_row_nos: Set[int] = set()

    def reset(self):
        """Reset state between tables."""
        self.seen_months.clear()
        self.seen_row_nos.clear()

    @staticmethod
    def parse_month(month_str: str) -> Optional[date]:
        """
        Parses month strings such as '2025-01', '2025-01-01', 'Jan 2025'.
        """
        if not month_str or not month_str.strip():
            return None
        cleaned = month_str.strip()

        # Try standard YYYY-MM-DD
        try:
            return datetime.strptime(cleaned, "%Y-%m-%d").date()
        except ValueError:
            pass

        # Try YYYY-MM (default day to 01)
        try:
            dt = datetime.strptime(cleaned, "%Y-%m")
            return dt.date()
        except ValueError:
            pass

        # Try YYYY/MM or YYYY/MM/DD
        try:
            return datetime.strptime(cleaned, "%Y/%m/%d").date()
        except ValueError:
            pass
        try:
            return datetime.strptime(cleaned, "%Y/%m").date()
        except ValueError:
            pass

        return None

    @staticmethod
    def parse_float_metric(val_str: Any) -> Tuple[Optional[float], Optional[str]]:
        """
        Parses a numeric metric (volume or value).
        Returns (parsed_float, error_status).
        If valid: (float_val, None)
        If missing: (None, 'missing')
        If bad number: (None, 'bad_number')
        """
        if val_str is None:
            return None, "missing"

        if isinstance(val_str, (int, float)):
            if val_str < 0:
                return None, "bad_number"
            return float(val_str), None

        s = str(val_str).strip()
        if not s or s.lower() in TradeRowValidator.MISSING_MARKERS:
            return None, "missing"

        # Check for bad characters or invalid format (e.g. "145.2x", "12,34.5", "abc")
        # Remove normal commas used as thousands separators
        s_clean = s.replace(",", "")
        try:
            val = float(s_clean)
            if val < 0:
                return None, "bad_number"
            return val, None
        except ValueError:
            return None, "bad_number"

    def validate_raw_row(
        self,
        table_id: str,
        row_no: int,
        month_raw: Any,
        volume_raw: Any,
        value_raw: Any,
        is_cut_off: bool = False,
    ) -> TradeRow:
        """
        Validates raw column values for a single row and returns a typed TradeRow.
        """
        if is_cut_off:
            return TradeRow(
                table_id=table_id,
                row_no=row_no,
                month=self.parse_month(str(month_raw)) or date(1970, 1, 1),
                volume=None,
                value=None,
                row_status="cut_off",
                flag_reason="Row truncated: missing required value/volume columns",
            )

        # Check for repeated row numbers
        if row_no in self.seen_row_nos:
            return TradeRow(
                table_id=table_id,
                row_no=row_no,
                month=self.parse_month(str(month_raw)) or date(1970, 1, 1),
                volume=None,
                value=None,
                row_status="repeated",
                flag_reason=f"Duplicate row number {row_no} detected in table",
            )
        self.seen_row_nos.add(row_no)

        # Parse month
        month_dt = self.parse_month(str(month_raw))
        if not month_dt:
            return TradeRow(
                table_id=table_id,
                row_no=row_no,
                month=date(1970, 1, 1),
                volume=None,
                value=None,
                row_status="bad_number",
                flag_reason=f"Invalid month format: '{month_raw}'",
            )

        # Check for repeated month
        month_key = month_dt.strftime("%Y-%m")
        if month_key in self.seen_months:
            return TradeRow(
                table_id=table_id,
                row_no=row_no,
                month=month_dt,
                volume=None,
                value=None,
                row_status="repeated",
                flag_reason=f"Duplicate month entry '{month_key}' detected in table",
            )
        self.seen_months.add(month_key)

        # Parse volume and value
        vol, vol_err = self.parse_float_metric(volume_raw)
        val, val_err = self.parse_float_metric(value_raw)

        if vol_err == "bad_number" or val_err == "bad_number":
            return TradeRow(
                table_id=table_id,
                row_no=row_no,
                month=month_dt,
                volume=vol,
                value=val,
                row_status="bad_number",
                flag_reason=f"Corrupt numeric entry: volume='{volume_raw}', value='{value_raw}'",
            )

        if vol_err == "missing" or val_err == "missing":
            return TradeRow(
                table_id=table_id,
                row_no=row_no,
                month=month_dt,
                volume=vol,
                value=val,
                row_status="missing",
                flag_reason=f"Missing metric value: volume='{volume_raw}', value='{value_raw}'",
            )

        return TradeRow(
            table_id=table_id,
            row_no=row_no,
            month=month_dt,
            volume=vol,
            value=val,
            row_status="ok",
            flag_reason=None,
        )
