from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class TradeRow(BaseModel):
    """
    Granular monthly trade flow row identified by TABLE-ID#row.
    """
    table_id: str = Field(..., description="Parent table identifier, e.g. TAB-E5-01")
    row_no: int = Field(..., ge=1, description="1-indexed row number")
    month: date = Field(..., description="Reported month (YYYY-MM-DD)")
    volume: Optional[float] = Field(default=None, description="Volume shipped (e.g. thousand metric tons)")
    value: Optional[float] = Field(default=None, description="Commercial trade value (e.g. million standard currency)")
    row_status: str = Field(default="ok", description="'ok', 'missing', 'bad_number', 'repeated', 'cut_off'")
    flag_reason: Optional[str] = Field(default=None, description="Reason if row_status != 'ok'")

    @property
    def citation_ref(self) -> str:
        return f"{self.table_id}#{self.row_no}"


class TradeTableHeader(BaseModel):
    """
    Metadata header of a fixed-layout trade table.
    """
    table_id: str = Field(..., description="Unique table ID, e.g. TAB-E5-01")
    country_pair: str = Field(..., description="e.g. 'Orvan-Midgard'")
    sector: str = Field(..., description="e.g. 'wheat', 'maize'")
    unit: str = Field(..., description="e.g. 'thousand_metric_tons'")
    period: str = Field(..., description="e.g. '2025-01_to_2027-01'")
    event_id: str = Field(default="NONE")
    status: str = Field(default="ok", description="'ok' or 'damaged'")
    source_file: Optional[str] = Field(default=None)


class MetricCalculationResult(BaseModel):
    """
    Deterministic mathematical result returned by compute_change tool.
    """
    table_id: str
    metric: str = Field(..., description="'value' or 'volume'")
    baseline_window: str = Field(..., description="e.g. '2025-01 to 2026-06'")
    baseline_average: float
    comparison_window: str = Field(..., description="e.g. '2026-07 to 2027-01'")
    comparison_average: float
    percentage_change: float = Field(..., description="Negative denotes drop, positive denotes growth")
    absolute_change: float
    rows_used: List[int] = Field(default_factory=list, description="List of row_no integers used in computation")
    rows_excluded: List[int] = Field(default_factory=list, description="Row numbers excluded (bad number, post as-of)")
    explanation: str
    citation_ref: str = Field(..., description="Exact citation string, e.g. TAB-E5-01#12-24")
