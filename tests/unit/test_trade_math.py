from datetime import date
import pytest

from src.schemas.trade import TradeRow, TradeTableHeader, MetricCalculationResult
from src.trade.validator import TradeRowValidator
from src.trade.table_parser import TradeTableParser
from src.trade.analytics import TradeAnalyticsEngine


CLEAN_TABLE_TEXT = """
TABLE_ID: TRD-E5-01
COUNTRY_PAIR: Orvan-Midgard
SECTOR: wheat
UNIT: thousand_metric_tons
PERIOD: 2025-01_to_2026-12
EVENT_ID: EVT-ORV-01
---
row_no | month | volume | value
1 | 2025-01-01 | 100.0 | 30.0
2 | 2025-02-01 | 110.0 | 33.0
3 | 2025-03-01 | 105.0 | 31.5
4 | 2025-04-01 | 100.0 | 30.0
5 | 2026-07-01 | 50.0  | 18.0
6 | 2026-08-01 | 55.0  | 19.5
7 | 2026-09-01 | 45.0  | 16.5
"""

DAMAGED_TABLE_TEXT = """
TABLE_ID: TRD-TRAP-02
COUNTRY_PAIR: Orvan-Tolan
SECTOR: maize
UNIT: thousand_metric_tons
PERIOD: 2025-01_to_2026-04
EVENT_ID: EVT-ORV-01
---
row_no | month | volume | value
1 | 2025-01-01 | 80.0 | 25.0
2 | 2025-02-01 | 85.0x | 26.0
3 | 2025-03-01 | N/A  | 24.0
4 | 2025-03-01 | 75.0 | 23.0
5 | 2025-04-01 | 70.0
"""


def test_trade_validator_clean_and_traps():
    validator = TradeRowValidator()

    # Clean row
    r1 = validator.validate_raw_row("TAB-01", 1, "2025-01-01", "120.5", "45.0")
    assert r1.row_status == "ok"
    assert r1.volume == 120.5
    assert r1.value == 45.0

    # Bad number
    r2 = validator.validate_raw_row("TAB-01", 2, "2025-02-01", "120.5corrupt", "45.0")
    assert r2.row_status == "bad_number"

    # Missing value
    r3 = validator.validate_raw_row("TAB-01", 3, "2025-03-01", "-", "45.0")
    assert r3.row_status == "missing"

    # Repeated month
    r4 = validator.validate_raw_row("TAB-01", 4, "2025-01-01", "110.0", "40.0")
    assert r4.row_status == "repeated"

    # Cut off row
    r5 = validator.validate_raw_row("TAB-01", 5, "2025-05-01", "100.0", None, is_cut_off=True)
    assert r5.row_status == "cut_off"


def test_trade_table_parser_clean():
    parser = TradeTableParser()
    header, rows = parser.parse_string(CLEAN_TABLE_TEXT)

    assert header.table_id == "TRD-E5-01"
    assert header.country_pair == "Orvan-Midgard"
    assert header.sector == "wheat"
    assert header.status == "ok"
    assert len(rows) == 7
    assert all(r.row_status == "ok" for r in rows)


def test_trade_table_parser_traps_detection():
    parser = TradeTableParser()
    header, rows = parser.parse_string(DAMAGED_TABLE_TEXT)

    assert header.table_id == "TRD-TRAP-02"
    assert len(rows) == 5

    # Row 1 is OK
    assert rows[0].row_status == "ok"
    # Row 2 has 85.0x -> bad_number
    assert rows[1].row_status == "bad_number"
    # Row 3 has N/A -> missing
    assert rows[2].row_status == "missing"
    # Row 4 repeats month 2025-03 -> repeated
    assert rows[3].row_status == "repeated"
    # Row 5 is cut off -> cut_off
    assert rows[4].row_status == "cut_off"


def test_compute_change_calculation():
    parser = TradeTableParser()
    _, rows = parser.parse_string(CLEAN_TABLE_TEXT)

    engine = TradeAnalyticsEngine()
    # Baseline: 2025-01 to 2025-04 -> [100.0, 110.0, 105.0, 100.0] -> avg = 103.75
    # Comparison: 2026-07 to 2026-09 -> [50.0, 55.0, 45.0] -> avg = 50.0
    # Abs change: 50.0 - 103.75 = -53.75
    # Pct change: (-53.75 / 103.75) * 100 = -51.81%
    res = engine.compute_change(
        table_id="TRD-E5-01",
        baseline_window=("2025-01", "2025-04"),
        comparison_window=("2026-07", "2026-09"),
        metric="volume",
        in_memory_rows=rows,
    )

    assert res.baseline_average == 103.75
    assert res.comparison_average == 50.0
    assert res.absolute_change == -53.75
    assert res.percentage_change == -51.81
    assert res.rows_used == [1, 2, 3, 4, 5, 6, 7]
    assert res.rows_excluded == []
    assert res.citation_ref == "TRD-E5-01#1-7"


def test_compute_change_clock_gate_and_trap_exclusion():
    parser = TradeTableParser()
    _, rows = parser.parse_string(CLEAN_TABLE_TEXT)

    engine = TradeAnalyticsEngine()
    # Simulated clock set to 2026-07-31:
    # Rows 6 (2026-08) and 7 (2026-09) must be excluded for clock violation!
    res = engine.compute_change(
        table_id="TRD-E5-01",
        baseline_window=("2025-01", "2025-04"),
        comparison_window=("2026-07", "2026-09"),
        metric="volume",
        as_of_date=date(2026, 7, 31),
        in_memory_rows=rows,
    )

    # Comparison should only include Row 5 (50.0)
    assert res.comparison_average == 50.0
    assert 6 in res.rows_excluded
    assert 7 in res.rows_excluded
    assert res.rows_used == [1, 2, 3, 4, 5]
