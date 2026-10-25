from datetime import date
import pytest

from src.agents.odin.sufficiency import OdinSufficiencyChecker
from src.schemas.case_file import CaseFile, RunRecord, EventScope
from src.schemas.claims import Claim
from src.schemas.rulings import Ruling, RulingOutcome, RulingBasis


def test_sufficiency_send_back_on_missing_scope():
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
        claims=[
            Claim(
                claim_id="CLM-01",
                agent="thor",
                text="Nordland grain exports dropped 30%.",
                country="Nordland",
                sector="Agriculture",
                citations=["DOC-01"],
            )
        ],
        rulings=[
            Ruling(
                ruling_id="R1",
                claim_id="CLM-01",
                outcome=RulingOutcome.UPHELD,
                basis=RulingBasis.SOURCED_FACT,
                reasoning="Verified citation.",
                refs_checked=["DOC-01"],
            )
        ],
    )

    status, missing = checker.evaluate_sufficiency(case, run)
    assert status == "send_back"
    assert "evidence_for_target_country_Vestri" in missing
    assert "evidence_for_target_sector_Energy" in missing


def test_sufficiency_passes_when_evidence_complete():
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
        claims=[
            Claim(
                claim_id="CLM-01",
                agent="thor",
                text="Grain exports dropped 30%.",
                country="Nordland",
                sector="Agriculture",
                citations=["DOC-01"],
            )
        ],
        rulings=[
            Ruling(
                ruling_id="R1",
                claim_id="CLM-01",
                outcome=RulingOutcome.UPHELD,
                basis=RulingBasis.SOURCED_FACT,
                reasoning="Verified citation.",
                refs_checked=["DOC-01"],
            )
        ],
    )

    status, missing = checker.evaluate_sufficiency(case, run)
    assert status == "sufficient"
    assert missing == []


def test_sufficiency_terminates_on_run_2():
    checker = OdinSufficiencyChecker()
    case = CaseFile(
        case_id="CASE-03",
        question="What is the impact on Vestri?",
        as_of=date(2026, 3, 15),
        scope=EventScope(
            event_id="E5",
            event_name="Event 5",
            target_countries=["Vestri"],
            target_sectors=["Energy"],
            as_of_date=date(2026, 3, 15),
        ),
        limits={"max_runs": 2},
    )
    # Even if gaps remain, on Run 2 hard limit terminates send-back loops
    run = RunRecord(
        run_no=2,
        claims=[],
        rulings=[],
    )

    status, missing = checker.evaluate_sufficiency(case, run)
    assert status == "sufficient"
    assert missing == []
