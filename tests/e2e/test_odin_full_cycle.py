from datetime import date
from pathlib import Path
import pytest

from src.agents.odin import OdinJudge
from src.tools.citation_tools import CitationValidator
from src.schemas.case_file import CaseFile, RunRecord, EventScope, CaseStatus
from src.schemas.claims import Claim, Attack, Defence, ClaimKind


@pytest.fixture
def test_validator():
    validator = CitationValidator()
    # Register mock documents
    validator.register_local_doc("DOC-E5-001", {
        "doc_id": "DOC-E5-001",
        "title": "Skagen Port Interruption",
        "content": "[P1] Port of Skagen interrupted container and grain loading. [P2] Two berths shut down.",
        "pub_date": "2026-03-02",
        "reliability_tier": 1,
        "is_retracted": False,
        "is_damaged": False,
        "is_injection_attempt": False,
    })
    validator.register_local_doc("DOC-E5-002", {
        "doc_id": "DOC-E5-002",
        "title": "Rail Diversion Notice",
        "content": "[P1] Rail freight corridor mobilized to redirect 30% of grain traffic.",
        "pub_date": "2026-03-05",
        "reliability_tier": 2,
        "is_retracted": False,
        "is_damaged": False,
        "is_injection_attempt": False,
    })
    validator.register_local_doc("DOC-E5-003", {
        "doc_id": "DOC-E5-003",
        "title": "Vestri Power Grid Failure",
        "content": "[P1] Vestri industrial power grid experienced secondary brownout.",
        "pub_date": "2026-03-07",
        "reliability_tier": 1,
        "is_retracted": False,
        "is_damaged": False,
        "is_injection_attempt": False,
    })
    validator.register_local_doc("DOC-E5-FAKE", {
        "doc_id": "DOC-E5-FAKE",
        "title": "Retracted Rumor",
        "content": "[P1] Rumor that entire northern fleet was destroyed.",
        "pub_date": "2026-03-01",
        "reliability_tier": 4,
        "is_retracted": True,
        "is_damaged": False,
        "is_injection_attempt": False,
    })

    # Register mock trade rows
    validator.register_local_trade_row("TRD-E5-01#04", {
        "table_id": "TRD-E5-01",
        "row_no": 4,
        "month": "2026-03-01",
        "volume": 68.0,
        "value": 22.1,
        "row_status": "ok",
    })

    return validator


def test_odin_full_two_run_cycle(test_validator, tmp_path):
    as_of = date(2026, 3, 15)
    judge = OdinJudge(citation_validator=test_validator, output_base_dir=tmp_path)

    # -------------------------------------------------------------------------
    # RUN 1: Gaps in scope (Vestri Energy missing) -> Should trigger send_back
    # -------------------------------------------------------------------------
    case = CaseFile(
        case_id="CASE-E2E-ODIN-01",
        question="What is the supply chain exposure for Nordland grain and Vestri energy?",
        as_of=as_of,
        scope=EventScope(
            event_id="E5",
            event_name="Skagen Disruption",
            target_countries=["Nordland", "Vestri"],
            target_sectors=["Agriculture", "Energy"],
            as_of_date=as_of,
        ),
        limits={"max_runs": 2},
    )

    run_1 = RunRecord(
        run_no=1,
        claims=[
            Claim(
                claim_id="CLM-THOR-R1-01",
                agent="thor",
                text="Nordland grain port loading halted at Skagen.",
                country="Nordland",
                sector="Agriculture",
                estimate_low=-40.0,
                estimate_high=-30.0,
                citations=["DOC-E5-001#P1"],
            ),
            Claim(
                claim_id="CLM-LOKI-R1-01",
                agent="loki",
                text="Rail corridor rerouting limits grain decline to -20% to -10%.",
                country="Nordland",
                sector="Agriculture",
                estimate_low=-20.0,
                estimate_high=-10.0,
                citations=["DOC-E5-002#P1"],
            ),
        ],
        attacks=[
            Attack(
                attack_id="ATK-THOR-R1-01",
                from_agent="thor",
                target_claim_id="CLM-LOKI-R1-01",
                grounds="bad_method",
                evidence_refs=["DOC-E5-001#P2"],
                text="Rail cannot offset all berths simultaneously.",
            )
        ],
        defences=[
            Defence(
                defence_id="DEF-LOKI-R1-01",
                attack_id="ATK-THOR-R1-01",
                response_type="new_evidence",
                new_refs=["DOC-E5-002#P1"],
                text="Rail logistics notice confirms dedicated diversion routes.",
            )
        ],
    )
    case.runs.append(run_1)

    # Execute Odin on Run 1
    updated_case, summary_1 = judge.evaluate_case(case, run_no=1)

    assert summary_1["action"] == "send_back"
    assert updated_case.runs[0].sufficiency == "send_back"
    assert "evidence_for_target_country_Vestri" in updated_case.runs[0].missing
    assert "evidence_for_target_sector_Energy" in updated_case.runs[0].missing
    assert len(updated_case.runs[0].rulings) == 2

    # -------------------------------------------------------------------------
    # RUN 2: Gaps filled with Vestri Energy claims + Concession on fake claim
    # -------------------------------------------------------------------------
    run_2 = RunRecord(
        run_no=2,
        claims=[
            # Inherited / refined Nordland claims
            Claim(
                claim_id="CLM-THOR-R2-01",
                agent="thor",
                text="Nordland grain trade decreased 32% as verified in trade tables.",
                country="Nordland",
                sector="Agriculture",
                kind=ClaimKind.CALCULATION,
                estimate_low=-35.0,
                estimate_high=-30.0,
                citations=["TRD-E5-01#04"],
            ),
            Claim(
                claim_id="CLM-LOKI-R2-01",
                agent="loki",
                text="Rail diversion confirms actual impact contained within -25% to -15%.",
                country="Nordland",
                sector="Agriculture",
                estimate_low=-25.0,
                estimate_high=-15.0,
                citations=["DOC-E5-002#P1"],
            ),
            # New Vestri Energy claims filling the gap
            Claim(
                claim_id="CLM-THOR-R2-02",
                agent="thor",
                text="Vestri industrial grid brownout reduced regional power output by 18%.",
                country="Vestri",
                sector="Energy",
                estimate_low=-20.0,
                estimate_high=-15.0,
                citations=["DOC-E5-003#P1"],
            ),
            # Trapped claim that Thor formally concedes
            Claim(
                claim_id="CLM-THOR-R2-03",
                agent="thor",
                text="Northern fleet completely decommissioned.",
                country="Nordland",
                sector="Maritime",
                citations=["DOC-E5-FAKE#P1"],
            ),
        ],
        attacks=[
            Attack(
                attack_id="ATK-LOKI-R2-02",
                from_agent="loki",
                target_claim_id="CLM-THOR-R2-03",
                grounds="retracted",
                evidence_refs=[],
                text="Article DOC-E5-FAKE was formally retracted by publisher.",
            )
        ],
        defences=[
            Defence(
                defence_id="DEF-THOR-R2-02",
                attack_id="ATK-LOKI-R2-02",
                response_type="concede",
                new_refs=[],
                text="Conceded: source was confirmed retracted.",
            )
        ],
    )
    case.runs.append(run_2)

    # Execute Odin on Run 2
    final_case, summary_2 = judge.evaluate_case(case, run_no=2)

    assert summary_2["action"] == "briefing_complete"
    assert final_case.status == CaseStatus.CLOSED
    assert final_case.runs[1].sufficiency == "sufficient"
    assert final_case.runs[1].missing == []

    # Check classifications
    classification = final_case.runs[1].classification
    assert "CLM-THOR-R2-01" in classification.established
    assert "CLM-THOR-R2-02" in classification.established
    assert "CLM-THOR-R2-03" in classification.conceded

    # Check ranges synthesized for both target countries
    ranges = final_case.runs[1].ranges
    countries_covered = {r.country for r in ranges}
    assert "Nordland" in countries_covered
    assert "Vestri" in countries_covered

    # Verify OKF Export Bundle
    export_bundle = summary_2["export_bundle"]
    assert "final_briefing_md" in export_bundle
    assert "case_file_json" in export_bundle
    assert "trap_scorecard" in export_bundle

    briefing_file = Path(export_bundle["final_briefing_md"])
    assert briefing_file.exists()
    content = briefing_file.read_text(encoding="utf-8")

    # Check OKF YAML frontmatter
    assert content.startswith("---")
    assert "case_id: CASE-E2E-ODIN-01" in content

    # Check Briefing content sections
    assert "## 1. Executive Summary" in content
    assert "## 2. Established Findings (Fact-Grounded)" in content
    assert "## 4. Conceded & Refuted Claims" in content
    assert "## 5. Calibrated Exposure Range Table" in content
    assert "## 7. Citation & Traceability Audit Log" in content
