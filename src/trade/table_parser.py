import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from src.schemas.trade import TradeTableHeader, TradeRow
from src.trade.validator import TradeRowValidator
from src.supabase_client import get_supabase_admin, get_supabase_client


class TradeTableParser:
    """
    Parser for Runemark fixed-layout trade tables.
    Extracts table metadata and monthly time-series rows with row-level damage detection.
    """

    HEADER_PATTERNS = {
        "table_id": re.compile(r"^(?:TABLE_ID|TABLE\s*ID):\s*(.+)$", re.IGNORECASE),
        "country_pair": re.compile(r"^(?:COUNTRY_PAIR|COUNTRY\s*PAIR):\s*(.+)$", re.IGNORECASE),
        "sector": re.compile(r"^SECTOR:\s*(.+)$", re.IGNORECASE),
        "unit": re.compile(r"^UNIT:\s*(.+)$", re.IGNORECASE),
        "period": re.compile(r"^PERIOD:\s*(.+)$", re.IGNORECASE),
        "event_id": re.compile(r"^(?:EVENT_ID|EVENT\s*ID):\s*(.+)$", re.IGNORECASE),
    }

    def __init__(self):
        self.validator = TradeRowValidator()
        self._admin = None

    @property
    def admin(self):
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    def parse_string(
        self,
        text: str,
        source_file: Optional[str] = None,
    ) -> Tuple[TradeTableHeader, List[TradeRow]]:
        """
        Parses text containing a fixed-layout trade table.
        Returns the parsed TradeTableHeader and List of TradeRow models.
        """
        self.validator.reset()
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]

        metadata: Dict[str, str] = {
            "table_id": "",
            "country_pair": "Unknown",
            "sector": "general",
            "unit": "thousand_metric_tons",
            "period": "unknown",
            "event_id": "NONE",
            "status": "ok",
        }

        row_lines: List[str] = []
        in_data_section = False
        columns_header_seen = False

        for line in lines:
            # Check for section separator
            if line.startswith("---") or line.startswith("==="):
                in_data_section = True
                continue

            if not in_data_section:
                matched_header = False
                for field, pattern in self.HEADER_PATTERNS.items():
                    m = pattern.match(line)
                    if m:
                        metadata[field] = m.group(1).strip()
                        matched_header = True
                        break
                if not matched_header:
                    # If line looks like column headers (e.g. contains month, volume, value)
                    lower_line = line.lower()
                    if "month" in lower_line and ("vol" in lower_line or "val" in lower_line):
                        in_data_section = True
                        columns_header_seen = True
            else:
                lower_line = line.lower()
                if not columns_header_seen and ("month" in lower_line and ("vol" in lower_line or "val" in lower_line)):
                    columns_header_seen = True
                    continue
                # Line is a data row
                row_lines.append(line)

        # Validate header metadata
        if not metadata.get("table_id"):
            # Try to derive from source_file or assign default
            if source_file:
                metadata["table_id"] = Path(source_file).stem
            else:
                metadata["table_id"] = "TRD-UNKNOWN"
            metadata["status"] = "damaged"

        table_id = metadata["table_id"]
        trade_rows: List[TradeRow] = []

        # Parse each data row
        auto_row_no = 1
        for line in row_lines:
            # Tokenize line by pipe '|', comma, or whitespace
            if "|" in line:
                tokens = [t.strip() for t in line.split("|") if t.strip()]
            elif "," in line:
                tokens = [t.strip() for t in line.split(",") if t.strip()]
            else:
                tokens = line.split()

            if not tokens:
                continue

            # Determine column positions
            # Expected format A: row_no, month, volume, value (4 tokens)
            # Expected format B: month, volume, value (3 tokens, auto row_no)
            # Expected format C: cut_off row (fewer than 3 tokens)
            if len(tokens) >= 4:
                try:
                    row_no = int(tokens[0])
                except ValueError:
                    row_no = auto_row_no
                month_raw = tokens[1]
                volume_raw = tokens[2]
                value_raw = tokens[3]
                is_cut_off = False
            elif len(tokens) == 3:
                # Could be (row_no, month, volume) [cut_off] OR (month, volume, value)
                month_attempt = self.validator.parse_month(tokens[0])
                if month_attempt:
                    row_no = auto_row_no
                    month_raw = tokens[0]
                    volume_raw = tokens[1]
                    value_raw = tokens[2]
                    is_cut_off = False
                else:
                    try:
                        row_no = int(tokens[0])
                    except ValueError:
                        row_no = auto_row_no
                    month_raw = tokens[1]
                    volume_raw = tokens[2]
                    value_raw = None
                    is_cut_off = True
            elif len(tokens) == 2:
                try:
                    row_no = int(tokens[0])
                    month_raw = tokens[1]
                except ValueError:
                    row_no = auto_row_no
                    month_raw = tokens[0]
                volume_raw = None
                value_raw = None
                is_cut_off = True
            else:
                row_no = auto_row_no
                month_raw = tokens[0] if tokens else "missing"
                volume_raw = None
                value_raw = None
                is_cut_off = True

            row = self.validator.validate_raw_row(
                table_id=table_id,
                row_no=row_no,
                month_raw=month_raw,
                volume_raw=volume_raw,
                value_raw=value_raw,
                is_cut_off=is_cut_off,
            )
            trade_rows.append(row)
            auto_row_no += 1

        # Check table-level health
        damaged_count = sum(1 for r in trade_rows if r.row_status != "ok")
        if not trade_rows or (damaged_count > 0 and damaged_count == len(trade_rows)):
            metadata["status"] = "damaged"

        header = TradeTableHeader(
            table_id=metadata["table_id"],
            country_pair=metadata["country_pair"],
            sector=metadata["sector"],
            unit=metadata["unit"],
            period=metadata["period"],
            event_id=metadata.get("event_id", "NONE"),
            status=metadata["status"],
            source_file=source_file,
        )

        return header, trade_rows

    def parse_file(self, file_path: Path) -> Tuple[TradeTableHeader, List[TradeRow]]:
        """Parses a trade table from a text file path."""
        p = Path(file_path)
        content = p.read_text(encoding="utf-8", errors="replace")
        return self.parse_string(content, source_file=p.name)

    def upsert_to_supabase(
        self,
        header: TradeTableHeader,
        rows: List[TradeRow],
    ) -> bool:
        """
        Upserts the parsed table header into `trade_tables` and rows into `trade_rows`.
        """
        header_row = {
            "table_id": header.table_id,
            "country_pair": header.country_pair,
            "sector": header.sector,
            "unit": header.unit,
            "period": header.period,
            "event_id": header.event_id,
            "status": header.status,
            "source_file": header.source_file,
        }

        try:
            self.admin.table("trade_tables").upsert(header_row, on_conflict="table_id").execute()
        except Exception as e:
            raise RuntimeError(f"Failed to upsert trade table header '{header.table_id}': {e}")

        # Prepare rows for upsert
        db_rows = []
        for r in rows:
            db_rows.append({
                "table_id": r.table_id,
                "row_no": r.row_no,
                "month": r.month.isoformat(),
                "volume": r.volume,
                "value": r.value,
                "row_status": r.row_status,
                "flag_reason": r.flag_reason,
            })

        if db_rows:
            try:
                # Upsert rows in batches
                batch_size = 50
                for i in range(0, len(db_rows), batch_size):
                    batch = db_rows[i : i + batch_size]
                    self.admin.table("trade_rows").upsert(batch, on_conflict="table_id,row_no").execute()
            except Exception as e:
                raise RuntimeError(f"Failed to upsert trade rows for table '{header.table_id}': {e}")

        return True
