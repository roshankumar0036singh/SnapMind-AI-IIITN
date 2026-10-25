"""
tests/unit/test_dossier_integration.py
======================================
Tests the complete end-to-end shared case dossier flow:
  1. Heimdall produces EvidenceIndexEntry candidates.
  2. Workflow persists Heimdall's evidence_index directly onto current_run.evidence_index.
  3. Thor and Loki consume current_run.evidence_index as Section 1 (baseline dossier).
  4. Thor and Loki still execute their own perspective search tools (Section 2 - Criterion 3).
  5. On Odin Send-Back with missing categories, Heimdall runs targeted searches and populates new_evidence.
"""

from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from src.schemas.case_file import (
    CaseFile,
    EventScope,
    VerificationVerdict,
    CaseStatus,
    RunRecord,
    EvidenceIndexEntry,
)
from src.agents.thor.thor_agent import ThorAgent
from src.agents.loki.loki_agent import LokiAgent
from src.engine.trial_workflow import run_convergence_debate


def test_workflow_bridges_heimdall_evidence_to_current_run(monkeypatch):
    case = CaseFile(
        case_id="CASE-DOSSIER-TEST-001",
        question="What is the exposure to the Orvan corridor collapse for Midgard wheat?",
        as_of=date(2027, 1, 25),
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Midgard"],
            target_sectors=["Wheat"],
            as_of_date=date(2027, 1, 25),
        ),
        budget={
            "max_debate_turns": 4,
            "max_tool_calls": 10,
            "max_tokens": 10000,
            "max_wall_seconds": 60,
            "max_stable_cycles": 1,
            "max_no_progress_cycles": 1,
            "evidence_runs": 0,
            "max_evidence_runs": 2,
        },
    )

    mock_entry = EvidenceIndexEntry(
        entry_id="ENTRY001",
        doc_id="ORV-0005",
        title="Ministry of Transport Corridors Closure Notice",
        tier="T1",
        date="2027-01-20",
        summary="Complete halt on northern rail transit.",
        usable=True,
        reliability_weight=1.0,
    )

    def fake_heimdall(*args, **kwargs):
        res = MagicMock()
        res.evidence_index = [mock_entry]
        res.new_evidence = []
        return res

    def fake_debate_agents(case, run_no=1):
        # Assert that current_run has the evidence_index populated by Heimdall
        current_run = case.runs[-1]
        assert len(current_run.evidence_index) == 1
        assert current_run.evidence_index[0].doc_id == "ORV-0005"
        return {"thor": "complete", "loki": "complete", "new_claims": True}

    def fake_odin(case, run_no=1):
        return {"sufficiency": "sufficient", "missing": [], "termination": "converged"}

    monkeypatch.setattr("src.engine.trial_workflow.run_heimdall", fake_heimdall)
    monkeypatch.setattr("src.engine.trial_workflow.run_debate_agents", fake_debate_agents)
    monkeypatch.setattr("src.engine.trial_workflow.run_odin", fake_odin)

    result = run_convergence_debate(case)
    assert len(result.runs[0].evidence_index) == 1
    assert result.runs[0].evidence_index[0].doc_id == "ORV-0005"


@pytest.mark.asyncio
async def test_thor_and_loki_consume_dossier_and_search_autonomously():
    as_of = date(2027, 1, 25)
    mock_entry = EvidenceIndexEntry(
        entry_id="ENTRY002",
        doc_id="ORV-0002",
        title="Port of Nordmark Grain Silo Damage",
        tier="T1",
        date="2027-01-18",
        summary="Structural damage to grain silos reduces loading capacity by 40%.",
        usable=True,
        reliability_weight=0.95,
    )

    case = CaseFile(
        case_id="CASE-DOSSIER-CONSUME-001",
        question="Assess supply chain exposure for Midgard wheat.",
        as_of=as_of,
        status=CaseStatus.OPEN,
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Midgard"],
            target_sectors=["Wheat"],
            as_of_date=as_of,
        ),
        verification=VerificationVerdict(
            verdict="real",
            confidence=1.0,
            reasons=["Verified"],
            supporting_docs=["ORV-0002"],
            message_to_user="Real disruption event.",
        ),
        runs=[RunRecord(run_no=1, evidence_index=[mock_entry])],
    )

    thor = ThorAgent()
    loki = LokiAgent()

    # Intercept call_gemini_structured to inspect the prompt received by Thor and Loki
    prompts_captured = {}

    def capture_thor_gemini(prompt, system_prompt, response_schema, temperature=0.1):
        prompts_captured["thor"] = prompt
        # Return mock structured output
        mock_out = MagicMock()
        mock_claim = MagicMock()
        mock_claim.agent = "thor"
        mock_claim.claim_id = "CLM-THOR-TEST-01"
        mock_claim.country = "Midgard"
        mock_claim.sector = "Wheat"
        mock_claim.estimate_low = 30.0
        mock_claim.estimate_high = 50.0
        mock_claim.unit = "percentage"
        mock_claim.confidence = 0.9
        mock_claim.kind = "sourced_fact"
        mock_claim.text = "Severe grain shortage due to silo damage."
        mock_claim.citations = ["ORV-0002"]
        mock_claim.model_dump.return_value = {"claim_id": "CLM-THOR-TEST-01"}
        mock_out.claims = [mock_claim]
        return mock_out

    def capture_loki_gemini(prompt, system_prompt, response_schema, temperature=0.1):
        prompts_captured["loki"] = prompt
        mock_out = MagicMock()
        mock_claim = MagicMock()
        mock_claim.agent = "loki"
        mock_claim.claim_id = "CLM-LOKI-TEST-01"
        mock_claim.country = "Midgard"
        mock_claim.sector = "Wheat"
        mock_claim.estimate_low = 5.0
        mock_claim.estimate_high = 15.0
        mock_claim.unit = "percentage"
        mock_claim.confidence = 0.85
        mock_claim.kind = "inference"
        mock_claim.text = "Commercial substitution buffers the impact."
        mock_claim.citations = ["ORV-0002"]
        mock_claim.model_dump.return_value = {"claim_id": "CLM-LOKI-TEST-01"}
        mock_out.claims = [mock_claim]
        return mock_out

    with patch.object(thor, "call_gemini_structured", side_effect=capture_thor_gemini):
        with patch.object(loki, "call_gemini_structured", side_effect=capture_loki_gemini):
            await thor.act(case)
            await loki.act(case)

    # 1. Verify Thor received Heimdall's dossier AND its own specialized search section
    assert "thor" in prompts_captured
    thor_prompt = prompts_captured["thor"]
    assert "SECTION 1: HEIMDALL SHARED CASE DOSSIER" in thor_prompt
    assert "ORV-0002" in thor_prompt
    assert "Port of Nordmark Grain Silo Damage" in thor_prompt
    assert "SECTION 2: THOR'S SPECIALIZED HIGH-EXPOSURE RETRIEVAL" in thor_prompt

    # 2. Verify Loki received Heimdall's dossier AND its own specialized search section
    assert "loki" in prompts_captured
    loki_prompt = prompts_captured["loki"]
    assert "SECTION 1: HEIMDALL SHARED CASE DOSSIER" in loki_prompt
    assert "ORV-0002" in loki_prompt
    assert "Port of Nordmark Grain Silo Damage" in loki_prompt
    assert "SECTION 2: LOKI'S SPECIALIZED RESILIENCE RETRIEVAL" in loki_prompt


def test_send_back_dossier_merge_and_brothers_receive_merged(monkeypatch):
    """
    Verifies that on Odin send-back:
      1. Odin returns 'insufficient' with missing categories.
      2. Heimdall receives the send_back_categories on Run 2.
      3. The workflow MERGES Run 1's dossier with Run 2's new evidence (no evidence is lost).
      4. The debate agents on Run 2 receive the combined dossier with both documents.
    """
    case = CaseFile(
        case_id="CASE-SENDBACK-MERGE-001",
        question="Assess supply chain exposure for Midgard wheat.",
        as_of=date(2027, 1, 25),
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Midgard"],
            target_sectors=["Wheat"],
            as_of_date=date(2027, 1, 25),
        ),
        budget={
            "max_debate_turns": 4,
            "max_tool_calls": 10,
            "max_tokens": 10000,
            "max_wall_seconds": 60,
            "max_stable_cycles": 1,
            "max_no_progress_cycles": 1,
            "evidence_runs": 0,
            "max_evidence_runs": 2,
        },
    )

    doc_run1 = EvidenceIndexEntry(
        entry_id="ENTRY001",
        doc_id="ORV-0001",
        title="Rail Corridor Primary Shutdown",
        tier="T1",
        date="2027-01-20",
        summary="Main rail trunk line closed.",
        usable=True,
        reliability_weight=1.0,
    )

    doc_run2 = EvidenceIndexEntry(
        entry_id="ENTRY002",
        doc_id="ORV-0002",
        title="Alternative Northern Feeder Route Status",
        tier="T1",
        date="2027-01-22",
        summary="Feeder route operational at 30% capacity.",
        usable=True,
        reliability_weight=0.9,
    )

    heimdall_calls = []
    debate_dossiers = []

    def fake_heimdall(*args, **kwargs):
        run_no = kwargs.get("run_no", 1)
        send_back_cats = kwargs.get("send_back_categories")
        heimdall_calls.append({"run_no": run_no, "categories": send_back_cats})

        res = MagicMock()
        if run_no == 1:
            res.evidence_index = [doc_run1]
            res.new_evidence = []
        else:
            # Run 2 adds doc_run2
            res.evidence_index = [doc_run2]
            res.new_evidence = [doc_run2]
        return res

    def fake_debate_agents(case, run_no=1):
        current_run = case.runs[-1]
        # Record the docs present in the current run's evidence_index
        doc_ids = [
            e.doc_id if hasattr(e, "doc_id") else (e.get("doc_id") if isinstance(e, dict) else str(e))
            for e in current_run.evidence_index
        ]
        debate_dossiers.append({"run_no": run_no, "doc_ids": doc_ids})
        return {"thor": "complete", "loki": "complete", "new_claims": True}

    def fake_odin(case, run_no=1):
        if run_no == 1:
            return {
                "sufficiency": "insufficient",
                "missing": ["rail_feeder_capacity"],
                "termination": None,
            }
        return {
            "sufficiency": "sufficient",
            "missing": [],
            "termination": "converged",
        }

    monkeypatch.setattr("src.engine.trial_workflow.run_heimdall", fake_heimdall)
    monkeypatch.setattr("src.engine.trial_workflow.run_debate_agents", fake_debate_agents)
    monkeypatch.setattr("src.engine.trial_workflow.run_odin", fake_odin)

    result = run_convergence_debate(case)

    # 1. Heimdall called twice
    assert len(heimdall_calls) == 2
    assert heimdall_calls[0]["run_no"] == 1
    assert heimdall_calls[1]["run_no"] == 2
    assert heimdall_calls[1]["categories"] == ["rail_feeder_capacity"]

    # 2. Debate agents called twice
    assert len(debate_dossiers) == 2
    # Run 1 debate only had ORV-0001
    assert debate_dossiers[0]["doc_ids"] == ["ORV-0001"]
    # Run 2 debate had BOTH ORV-0002 AND ORV-0001 (merged! no loss of Run 1!)
    assert "ORV-0001" in debate_dossiers[1]["doc_ids"]
    assert "ORV-0002" in debate_dossiers[1]["doc_ids"]

    # 3. Final case status converged
    assert result.termination is not None
    assert result.termination.reason.value == "converged"


def test_tier_1_conflicting_evidence_odin_contested_and_sendback():
    """
    Verifies that when both Thor and Loki present Tier 1 verified evidence:
      1. Adjudicator marks findings as CONTESTED (not rejected, not conceded).
      2. Classifier places them in 'contested' and widens calibrated ranges.
      3. Sufficiency checker detects multi-party contradiction and issues 'insufficient'
         with missing category 'tier_1_official_resolution_for_contested_facts'.
      4. Odin Judge issues 'send_back'.
    """
    from src.schemas.claims import Claim, Attack, Defence, ClaimKind
    from src.schemas.rulings import RulingOutcome
    from src.agents.odin.adjudicator import OdinAdjudicator
    from src.agents.odin.classifier import OdinClassifier
    from src.agents.odin.sufficiency import OdinSufficiencyChecker
    from src.agents.odin.agent import OdinJudge

    as_of = date(2027, 1, 25)

    # 1. Thor makes High Exposure claim; Loki makes Limited Exposure claim (both Tier 1)
    claim_1 = Claim(
        claim_id="CLM-THOR-T1-01",
        agent="thor",
        country="Midgard",
        sector="Wheat",
        kind=ClaimKind.SOURCED_FACT,
        estimate_low=35.0,
        estimate_high=50.0,
        confidence=0.95,
        text="Ministry decree confirms 45% rail capacity lost.",
        citations=["ORV-0001"],
    )
    claim_2 = Claim(
        claim_id="CLM-LOKI-T1-01",
        agent="loki",
        country="Midgard",
        sector="Wheat",
        kind=ClaimKind.SOURCED_FACT,
        estimate_low=5.0,
        estimate_high=15.0,
        confidence=0.90,
        text="Ministry bulletin confirms strategic reserve release limits net wheat exposure to 5-15%.",
        citations=["ORV-0002"],
    )

    # 2. Loki attacks Thor's claim; Thor attacks Loki's claim (both citing Tier 1 counter-evidence)
    attack_1 = Attack(
        attack_id="ATK-LOKI-01",
        from_agent="loki",
        target_claim_id="CLM-THOR-T1-01",
        grounds="alternative_routes",
        text="Official railway bulletin confirms bypass line is active.",
        evidence_refs=["ORV-0003"],
    )
    attack_2 = Attack(
        attack_id="ATK-THOR-01",
        from_agent="thor",
        target_claim_id="CLM-LOKI-T1-01",
        grounds="buffer_stocks",
        text="Strategic grain reserve release is subject to canal draft restrictions.",
        evidence_refs=["ORV-0004"],
    )

    # 3. Thor defends against attack_1; Loki defends against attack_2 (both with valid Tier 1 evidence)
    defence_1 = Defence(
        defence_id="DEF-THOR-01",
        attack_id="ATK-LOKI-01",
        response_type="new_evidence",
        text="Bypass line has electric gauge mismatch limiting throughput.",
        new_refs=["ORV-0005"],
    )
    defence_2 = Defence(
        defence_id="DEF-LOKI-01",
        attack_id="ATK-THOR-01",
        response_type="new_evidence",
        text="Shallow draft barges deployed by maritime authority maintain transport flow.",
        new_refs=["ORV-0006"],
    )

    # Mock CitationValidator so all Tier 1 citations are valid
    mock_validator = MagicMock()
    mock_resp = MagicMock()
    mock_resp.is_valid = True
    mock_resp.reason = "Valid Tier 1 official notice"
    mock_validator.verify_citation.return_value = mock_resp

    # Test Adjudicator
    adjudicator = OdinAdjudicator(citation_validator=mock_validator)
    rulings = adjudicator.adjudicate_claims(
        claims=[claim_1, claim_2],
        attacks=[attack_1, attack_2],
        defences=[defence_1, defence_2],
        as_of=as_of,
        run_no=1,
    )

    assert len(rulings) == 2
    assert rulings[0].outcome == RulingOutcome.CONTESTED
    assert rulings[1].outcome == RulingOutcome.CONTESTED
    assert "both sides" in rulings[0].reasoning.lower() or "contested" in rulings[0].reasoning.lower()

    # Test Classifier
    classifier = OdinClassifier()
    classification = classifier.classify_findings(rulings)
    assert len(classification.contested) == 2
    assert "CLM-THOR-T1-01" in classification.contested
    assert "CLM-LOKI-T1-01" in classification.contested

    scope = EventScope(
        event_id="E5",
        event_name="Orvan grain corridor collapse",
        target_countries=["Midgard"],
        target_sectors=["Wheat"],
        as_of_date=as_of,
    )
    ranges = classifier.synthesize_ranges(
        claims=[claim_1, claim_2],
        rulings=rulings,
        scope=scope,
    )
    assert len(ranges) >= 1
    # Check that basis explicitly notes the contested nature
    assert "contested" in ranges[0].basis.lower()

    # Test Sufficiency Checker
    run_record = RunRecord(
        run_no=1,
        claims=[claim_1, claim_2],
        attacks=[attack_1, attack_2],
        defences=[defence_1, defence_2],
        rulings=rulings,
        classification=classification,
        ranges=ranges,
    )
    case_file = CaseFile(
        case_id="CASE-TIER1-CONFLICT-001",
        question="What is the exposure to Midgard wheat?",
        as_of=as_of,
        scope=scope,
        runs=[run_record],
        budget={
            "max_debate_turns": 4,
            "max_tool_calls": 10,
            "max_tokens": 10000,
            "max_wall_seconds": 60,
            "max_stable_cycles": 1,
            "max_no_progress_cycles": 1,
            "evidence_runs": 0,
            "max_evidence_runs": 3,
        },
    )

    checker = OdinSufficiencyChecker()
    status, missing = checker.evaluate_sufficiency(case_file=case_file, run_record=run_record)
    assert status == "insufficient"
    assert "tier_1_official_resolution_for_contested_facts" in missing

    # Test complete OdinJudge
    judge = OdinJudge(citation_validator=mock_validator)
    evaluated_case, result_summary = judge.evaluate_case(case_file=case_file, run_no=1)
    assert result_summary["action"] == "send_back"
    assert result_summary["sufficiency"] == "insufficient"
    assert "tier_1_official_resolution_for_contested_facts" in result_summary["missing"]

