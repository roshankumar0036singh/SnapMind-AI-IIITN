from datetime import date

from src.schemas.case_file import CaseFile, EventScope, RunRecord
from src.agents.odin.sufficiency import OdinSufficiencyChecker


def test_safety_limit_with_unresolved_gap_closes_incomplete():
    checker = OdinSufficiencyChecker()

    case = CaseFile(
        case_id="CASE-LIMIT-001",
        question="Assess Tolan maize exposure.",
        as_of=date(2027, 1, 25),
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Tolan"],
            target_sectors=["Maize"],
            as_of_date=date(2027, 1, 25),
        ),
        budget={
            "max_debate_turns": 2,
            "max_tool_calls": 5,
            "max_tokens": 1000,
            "max_wall_seconds": 10,
            "max_stable_cycles": 1,
            "max_no_progress_cycles": 1,
            "evidence_runs": 3,
            "max_evidence_runs": 3,
        },
    )

    run = RunRecord(
        run_no=3,
        claims=[],
        rulings=[],
    )

    status, missing = checker.evaluate_sufficiency(case, run)

    assert status in {"insufficient", "incomplete"}
    assert status != "sufficient"
    assert missing
