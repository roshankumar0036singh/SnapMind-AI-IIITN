from datetime import date

from src.schemas.case_file import CaseFile, EventScope
from src.engine.trial_workflow import run_convergence_debate


def test_insufficient_odin_result_wakes_heimdall_and_continues(monkeypatch):
    events = []

    case = CaseFile(
        case_id="CASE-SENDBACK-002",
        question="Assess Midgard and Tolan wheat and maize exposure.",
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
            "evidence_runs": 0,
            "max_evidence_runs": 3,
        },
    )

    def fake_heimdall(*args, **kwargs):
        run_no = kwargs.get("run_no", 1)
        events.append(f"heimdall_run_{run_no}")

        if run_no == 1:
            return {
                "status": "real",
                "new_evidence": [],
                "evidence_gaps": [
                    "Tolan maize replacement capacity"
                ],
            }

        return {
            "status": "real",
            "new_evidence": ["ORV-0030", "ORV-0027"],
            "evidence_gaps": [],
        }

    def fake_debate_agents(*args, **kwargs):
        run_no = kwargs.get("run_no", 1)
        events.append(f"debate_run_{run_no}")
        return {
            "thor": "complete",
            "loki": "complete",
            "new_claims": run_no == 2,
        }

    def fake_odin(*args, **kwargs):
        run_no = kwargs.get("run_no", 1)
        events.append(f"odin_run_{run_no}")

        if run_no == 1:
            return {
                "sufficiency": "insufficient",
                "missing": ["Tolan maize replacement capacity"],
                "termination": None,
            }

        return {
            "sufficiency": "sufficient",
            "missing": [],
            "termination": "converged",
        }

    # Replace these monkeypatch targets with the actual functions used
    # by your rewritten trial_workflow.py.
    monkeypatch.setattr(
        "src.engine.trial_workflow.run_heimdall",
        fake_heimdall,
    )
    monkeypatch.setattr(
        "src.engine.trial_workflow.run_debate_agents",
        fake_debate_agents,
    )
    monkeypatch.setattr(
        "src.engine.trial_workflow.run_odin",
        fake_odin,
    )

    result = run_convergence_debate(case)

    assert "odin_run_1" in events
    assert "heimdall_run_2" in events
    assert "debate_run_2" in events
    assert "odin_run_2" in events

    assert events.index("odin_run_1") < events.index("heimdall_run_2")
    assert events.index("heimdall_run_2") < events.index("debate_run_2")

    assert result.termination is not None
    assert result.termination.reason == "converged"
