"""
tests/unit/test_odin_sufficiency.py
====================================
Unit tests for OdinSufficiencyChecker (FR4.3).

Tests evaluate evidence quality only — the checker no longer controls
loop termination. It returns 'sufficient' or 'insufficient'.
"""

from datetime import date

import pytest

from src.agents.odin.sufficiency import OdinSufficiencyChecker
from src.schemas.case_file import CaseFile, RunRecord, EventScope
from src.schemas.claims import Claim
from src.schemas.rulings import Ruling, RulingOutcome, RulingBasis


def _make_claim(claim_id: str, agent: str, country: str, sector: str, status: str = "submitted") -> Claim:
    return Claim(
        claim_id=claim_id,
        agent=agent,
        text=f"Claim from {agent} about {country}/{sector}.",
        country=country,
        sector=sector,
        citations=["DOC-01"],
        status=status,
    )


def _make_ruling(ruling_id: str, claim_id: str, outcome: RulingOutcome) -> Ruling:
    return Ruling(
        ruling_id=ruling_id,
        claim_id=claim_id,
        outcome=outcome,
        basis=RulingBasis.SOURCED_FACT,
        reasoning="Verified citation.",
        refs_checked=["DOC-01"],
    )


# ---------------------------------------------------------------------------
# Missing scope coverage → insufficient
# ---------------------------------------------------------------------------

def test_insufficient_on_missing_scope():
    """Checker returns 'insufficient' when target country/sector is uncovered."""
    checker = OdinSufficiencyChecker()
    case = CaseFile(
        case_id="CASE-01",
        question="What is the impact of Event 5 on Nordland grain and Vestri energy?",
        as_of=date(2026, 3, 15),
        scope=EventScope(
            event_id="E5",
            event_name="Event 5",
            target_countries=["Nordland", "Vestri"],
            target_sectors=["Agriculture", "Energy"],
            as_of_date=date(2026, 3, 15),
        ),
    )
    # Run 1 only covered Nordland Agriculture
    run = RunRecord(
        run_no=1,
        claims=[_make_claim("CLM-01", "thor", "Nordland", "Agriculture")],
        rulings=[_make_ruling("R1", "CLM-01", RulingOutcome.UPHELD)],
    )

    status, missing = checker.evaluate_sufficiency(case, run)
    assert status == "insufficient"
    assert "evidence_for_target_country_Vestri" in missing
    assert "evidence_for_target_sector_Energy" in missing


# ---------------------------------------------------------------------------
# Full scope coverage → sufficient
# ---------------------------------------------------------------------------

def test_sufficient_when_evidence_complete():
    """Checker returns 'sufficient' when all scope countries and sectors are covered."""
    checker = OdinSufficiencyChecker()
    case = CaseFile(
        case_id="CASE-02",
        question="What is the impact on Nordland grain?",
        as_of=date(2026, 3, 15),
        scope=EventScope(
            event_id="E5",
            event_name="Event 5",
            target_countries=["Nordland"],
            target_sectors=["Agriculture"],
            as_of_date=date(2026, 3, 15),
        ),
    )
    run = RunRecord(
        run_no=1,
        claims=[_make_claim("CLM-01", "thor", "Nordland", "Agriculture")],
        rulings=[_make_ruling("R1", "CLM-01", RulingOutcome.UPHELD)],
    )

    status, missing = checker.evaluate_sufficiency(case, run)
    assert status == "sufficient"
    assert missing == []


# ---------------------------------------------------------------------------
# No upheld or contested rulings → insufficient (admissibility gate)
# ---------------------------------------------------------------------------

def test_insufficient_when_no_upheld_claims():
    """If no claims are upheld or contested, the admissibility gate fires."""
    checker = OdinSufficiencyChecker()
    case = CaseFile(
        case_id="CASE-03",
        question="Wheat impact on Midgard?",
        as_of=date(2027, 1, 25),
        scope=EventScope(
            event_id="E5",
            event_name="Orvan Corridor End",
            target_countries=["Midgard"],
            target_sectors=["wheat"],
            as_of_date=date(2027, 1, 25),
        ),
    )
    run = RunRecord(
        run_no=1,
        claims=[_make_claim("CLM-01", "thor", "Midgard", "wheat")],
        rulings=[_make_ruling("R1", "CLM-01", RulingOutcome.REJECTED)],
    )

    status, missing = checker.evaluate_sufficiency(case, run)
    assert status == "insufficient"
    assert "admissible_evidence_no_claims_upheld" in missing


# ---------------------------------------------------------------------------
# Checker does NOT control loop termination (old max_runs logic removed)
# ---------------------------------------------------------------------------

def test_checker_does_not_terminate_loop_on_any_run_number():
    """
    Checker must NOT return 'sufficient' just because run_no >= some max.
    Loop termination is exclusively the runner's responsibility.
    Even on run_no=99, if evidence is missing, checker returns 'insufficient'.
    """
    checker = OdinSufficiencyChecker()
    case = CaseFile(
        case_id="CASE-04",
        question="Maize impact on Tolan?",
        as_of=date(2027, 1, 25),
        scope=EventScope(
            event_id="E5",
            event_name="Orvan Corridor End",
            target_countries=["Tolan"],
            target_sectors=["maize"],
            as_of_date=date(2027, 1, 25),
        ),
    )
    # Even run_no=99 with no claims → still insufficient
    run = RunRecord(
        run_no=99,
        claims=[],
        rulings=[],
    )

    status, missing = checker.evaluate_sufficiency(case, run)
    assert status == "insufficient"
    assert len(missing) > 0  # Should report scope and admissibility gaps


# ---------------------------------------------------------------------------
# Two countries two sectors all covered → sufficient
# ---------------------------------------------------------------------------

def test_sufficient_two_countries_two_sectors():
    """Full multi-country multi-sector coverage returns sufficient."""
    checker = OdinSufficiencyChecker()
    case = CaseFile(
        case_id="CASE-05",
        question="Wheat and maize exposure for Midgard and Tolan?",
        as_of=date(2027, 1, 25),
        scope=EventScope(
            event_id="E5",
            event_name="Orvan Corridor End",
            target_countries=["Midgard", "Tolan"],
            target_sectors=["wheat", "maize"],
            as_of_date=date(2027, 1, 25),
        ),
    )
    run = RunRecord(
        run_no=1,
        claims=[
            _make_claim("CLM-01", "thor", "Midgard", "wheat"),
            _make_claim("CLM-02", "thor", "Tolan", "maize"),
            _make_claim("CLM-03", "loki", "Midgard", "wheat"),
            _make_claim("CLM-04", "loki", "Tolan", "maize"),
        ],
        rulings=[
            _make_ruling("R1", "CLM-01", RulingOutcome.UPHELD),
            _make_ruling("R2", "CLM-02", RulingOutcome.UPHELD),
            _make_ruling("R3", "CLM-03", RulingOutcome.CONTESTED),
            _make_ruling("R4", "CLM-04", RulingOutcome.CONTESTED),
        ],
    )

    status, missing = checker.evaluate_sufficiency(case, run)
    assert status == "sufficient"
    assert missing == []
