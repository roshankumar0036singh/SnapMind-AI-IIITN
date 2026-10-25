from datetime import date

from src.schemas.case_file import CaseFile, EventScope, RunRecord
from src.schemas.claims import Claim
from src.schemas.rulings import Ruling, RulingOutcome, RulingBasis
from src.agents.odin.sufficiency import OdinSufficiencyChecker


def test_odin_insufficient_evidence_triggers_sendback_not_successful_closure():
    checker = OdinSufficiencyChecker()

    case = CaseFile(
        case_id="CASE-SENDBACK-001",
        question=(
            "As of 25 January 2027, how exposed are Midgard and Tolan "
            "to the end of the Orvan corridor agreement?"
        ),
        as_of=date(2027, 1, 25),
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Midgard", "Tolan"],
            target_sectors=["Wheat", "Maize"],
            as_of_date=date(2027, 1, 25),
        ),
        budget={
            "max_debate_turns": 16,
            "max_tool_calls": 40,
            "max_tokens": 50000,
            "max_wall_seconds": 300,
            "max_stable_cycles": 2,
            "max_no_progress_cycles": 3,
            "evidence_runs": 1,
            "max_evidence_runs": 3,
        },
    )

    # Run 1 covers only Midgard wheat.
    run = RunRecord(
        run_no=1,
        claims=[
            Claim(
                claim_id="CLM-THOR-R1-001",
                agent="thor",
                text="Midgard wheat imports from Orvan declined materially.",
                country="Midgard",
                sector="Wheat",
                citations=["ORV-0009"],
            )
        ],
        rulings=[
            Ruling(
                ruling_id="RUL-ODIN-R1-001",
                claim_id="CLM-THOR-R1-001",
                outcome=RulingOutcome.UPHELD,
                basis=RulingBasis.SOURCED_FACT,
                reasoning="The claim is supported by a valid in-scope document.",
                refs_checked=["ORV-0009"],
            )
        ],
    )

    status, missing = checker.evaluate_sufficiency(case, run)

    assert status == "insufficient"
    assert missing

    assert "evidence_for_target_country_Tolan" in missing
    assert "evidence_for_target_sector_Maize" in missing

    # Odin must not claim that the case is sufficient merely because
    # the first run completed.
    assert status != "sufficient"
