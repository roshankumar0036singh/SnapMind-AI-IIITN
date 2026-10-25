"""
tests/unit/test_debate_convergence.py
======================================
Unit tests for the open-ended, state-driven convergence debate loop.

Tests cover:
  - DebateBudget schema and budget exhaustion checks
  - Canonical state fingerprinting
  - Convergence condition detection
  - Stall detection (stable cycles + no-progress cycles)
  - Safety budget limit detection (turns, tool calls, tokens, wall time)
  - DebateTerminationState construction
  - CaseFile integration with DebateBudget and DebateTerminationState
  - runner utility functions (compute_fingerprint, is_debate_converged)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import date, datetime, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.debate import (
    DebateBudget,
    DebateTerminationReason,
    DebateTerminationState,
    DebatePhase,
    DebateTurnRecord,
)
from src.schemas.case_file import CaseFile, CaseStatus, EventScope, RunRecord
from src.schemas.claims import Claim, Attack, Defence, ClaimKind
from src.engine.trial_workflow import compute_fingerprint, is_debate_converged


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_case(case_id: str = "CASE-TEST") -> CaseFile:
    return CaseFile(
        case_id=case_id,
        question="What is the exposure of Midgard to the Orvan corridor agreement ending?",
        as_of=date(2027, 1, 25),
        scope=EventScope(
            event_id="E5",
            event_name="Orvan Corridor Agreement End",
            target_countries=["Midgard", "Tolan"],
            target_sectors=["wheat", "maize"],
            as_of_date=date(2027, 1, 25),
        ),
        runs=[RunRecord(run_no=1)],
    )


def _make_claim(
    claim_id: str,
    agent: str = "thor",
    country: str = "Midgard",
    sector: str = "wheat",
    status: str = "attacked",
) -> Claim:
    return Claim(
        claim_id=claim_id,
        agent=agent,
        text=f"Claim {claim_id} from {agent}: disruption to {country}/{sector}.",
        country=country,
        sector=sector,
        citations=["DOC-01"],
        status=status,
    )


def _make_attack(attack_id: str, from_agent: str, target_claim_id: str) -> Attack:
    return Attack(
        attack_id=attack_id,
        from_agent=from_agent,
        target_claim_id=target_claim_id,
        grounds="contradicted",
        evidence_refs=["DOC-02"],
        text=f"Attack {attack_id} challenges {target_claim_id}.",
    )


def _make_defence(defence_id: str, attack_id: str, response_type: str = "new_evidence") -> Defence:
    return Defence(
        defence_id=defence_id,
        attack_id=attack_id,
        response_type=response_type,
        new_refs=["DOC-03"] if response_type == "new_evidence" else [],
        text=f"Defence {defence_id} answers {attack_id}.",
    )


# ===========================================================================
# DebateBudget Tests
# ===========================================================================

class TestDebateBudget:
    def test_default_budget_values(self):
        budget = DebateBudget()
        assert budget.max_debate_turns == 12
        assert budget.max_tool_calls == 40
        assert budget.max_tokens == 120_000
        assert budget.max_wall_seconds == 300.0
        assert budget.max_stable_cycles == 2
        assert budget.max_no_progress_cycles == 3
        assert budget.turns_used == 0
        assert budget.tool_calls_used == 0
        assert budget.tokens_used == 0
        assert budget.wall_seconds_used == 0.0
        assert budget.stable_cycles == 0
        assert budget.no_progress_cycles == 0
        assert budget.limit_hit is None

    def test_budget_not_exhausted_initially(self):
        budget = DebateBudget()
        assert not budget.is_any_limit_hit()

    def test_turns_limit_hit(self):
        budget = DebateBudget(max_debate_turns=4)
        budget.turns_used = 4
        assert budget.is_any_limit_hit()

    def test_tool_calls_limit_hit(self):
        budget = DebateBudget(max_tool_calls=10)
        budget.tool_calls_used = 10
        assert budget.is_any_limit_hit()

    def test_tokens_limit_hit(self):
        budget = DebateBudget(max_tokens=5_000)
        budget.tokens_used = 5_000
        assert budget.is_any_limit_hit()

    def test_wall_seconds_limit_hit(self):
        budget = DebateBudget(max_wall_seconds=60.0)
        budget.wall_seconds_used = 60.0
        assert budget.is_any_limit_hit()

    def test_budget_not_hit_below_limits(self):
        budget = DebateBudget(max_debate_turns=10, max_tool_calls=20)
        budget.turns_used = 9
        budget.tool_calls_used = 19
        assert not budget.is_any_limit_hit()

    def test_stall_detection_stable_cycles(self):
        budget = DebateBudget(max_stable_cycles=2)
        budget.stable_cycles = 2
        assert budget.is_stalled()

    def test_stall_detection_no_progress_cycles(self):
        budget = DebateBudget(max_no_progress_cycles=3)
        budget.no_progress_cycles = 3
        assert budget.is_stalled()

    def test_not_stalled_below_thresholds(self):
        budget = DebateBudget(max_stable_cycles=2, max_no_progress_cycles=3)
        budget.stable_cycles = 1
        budget.no_progress_cycles = 2
        assert not budget.is_stalled()

    def test_budget_custom_overrides(self):
        budget = DebateBudget(
            max_debate_turns=6,
            max_wall_seconds=120.0,
            max_stable_cycles=1,
        )
        assert budget.max_debate_turns == 6
        assert budget.max_wall_seconds == 120.0
        assert budget.max_stable_cycles == 1

    def test_budget_validation_min_turns(self):
        with pytest.raises(Exception):
            DebateBudget(max_debate_turns=1)  # ge=2 constraint

    def test_budget_validation_min_tool_calls(self):
        with pytest.raises(Exception):
            DebateBudget(max_tool_calls=3)  # ge=4 constraint


# ===========================================================================
# Canonical Fingerprint Tests
# ===========================================================================

class TestCanonicalFingerprint:
    def test_empty_run_has_stable_fingerprint(self):
        run = RunRecord(run_no=1)
        fp1 = compute_fingerprint(run)
        fp2 = compute_fingerprint(run)
        assert fp1 == fp2

    def test_fingerprint_changes_on_new_claim(self):
        run = RunRecord(run_no=1)
        fp_before = compute_fingerprint(run)
        run.claims.append(_make_claim("CLM-01", "thor"))
        fp_after = compute_fingerprint(run)
        assert fp_before != fp_after

    def test_fingerprint_changes_on_new_attack(self):
        run = RunRecord(run_no=1, claims=[_make_claim("CLM-01", "loki")])
        fp_before = compute_fingerprint(run)
        run.attacks.append(_make_attack("ATK-01", "thor", "CLM-01"))
        fp_after = compute_fingerprint(run)
        assert fp_before != fp_after

    def test_fingerprint_changes_on_new_defence(self):
        run = RunRecord(
            run_no=1,
            claims=[_make_claim("CLM-01", "loki")],
            attacks=[_make_attack("ATK-01", "thor", "CLM-01")],
        )
        fp_before = compute_fingerprint(run)
        run.defences.append(_make_defence("DEF-LOKI-01", "ATK-01"))
        fp_after = compute_fingerprint(run)
        assert fp_before != fp_after

    def test_fingerprint_is_deterministic_regardless_of_insertion_order(self):
        """Two runs with the same items in different insertion order must share fingerprint."""
        run1 = RunRecord(run_no=1)
        run1.claims.extend([
            _make_claim("CLM-01", "thor"),
            _make_claim("CLM-02", "loki"),
        ])

        run2 = RunRecord(run_no=1)
        run2.claims.extend([
            _make_claim("CLM-02", "loki"),
            _make_claim("CLM-01", "thor"),
        ])

        assert compute_fingerprint(run1) == compute_fingerprint(run2)

    def test_fingerprint_length_is_16_chars(self):
        run = RunRecord(run_no=1)
        fp = compute_fingerprint(run)
        assert len(fp) == 16

    def test_claim_status_change_changes_fingerprint(self):
        """A claim status change (submitted → attacked) must change the fingerprint."""
        run = RunRecord(run_no=1)
        run.claims.append(_make_claim("CLM-01", "thor", status="submitted"))
        fp_submitted = compute_fingerprint(run)

        run.claims[0].status = "attacked"
        fp_attacked = compute_fingerprint(run)
        assert fp_submitted != fp_attacked


# ===========================================================================
# Convergence Detection Tests
# ===========================================================================

class TestConvergenceDetection:
    def test_not_converged_with_no_claims(self):
        run = RunRecord(run_no=1)
        assert not is_debate_converged(run)

    def test_not_converged_with_only_thor_claims(self):
        run = RunRecord(run_no=1, claims=[_make_claim("CLM-01", "thor", status="attacked")])
        assert not is_debate_converged(run)

    def test_not_converged_with_only_loki_claims(self):
        run = RunRecord(run_no=1, claims=[_make_claim("CLM-01", "loki", status="attacked")])
        assert not is_debate_converged(run)

    def test_not_converged_when_undefended_attacks_exist(self):
        """If an attack has no defence, debate is not converged."""
        run = RunRecord(run_no=1)
        run.claims.extend([
            _make_claim("CLM-01", "thor", status="attacked"),
            _make_claim("CLM-02", "loki", status="attacked"),
        ])
        run.attacks.append(_make_attack("ATK-01", "thor", "CLM-02"))
        # No defence for ATK-01 → not converged
        assert not is_debate_converged(run)

    def test_not_converged_when_claims_still_submitted(self):
        """Claims with status 'submitted' mean the debate is still open."""
        run = RunRecord(run_no=1)
        run.claims.extend([
            _make_claim("CLM-01", "thor", status="submitted"),  # not yet attacked
            _make_claim("CLM-02", "loki", status="attacked"),
        ])
        run.attacks.append(_make_attack("ATK-01", "thor", "CLM-02"))
        run.defences.append(_make_defence("DEF-LOKI-01", "ATK-01"))
        assert not is_debate_converged(run)

    def test_converged_when_all_attacks_defended_and_no_submitted(self):
        """Convergence: both sides have claims, all attacks defended, no 'submitted' claims."""
        run = RunRecord(run_no=1)
        run.claims.extend([
            _make_claim("CLM-01", "thor", status="attacked"),
            _make_claim("CLM-02", "loki", status="attacked"),
        ])
        run.attacks.extend([
            _make_attack("ATK-LOKI-01", "loki", "CLM-01"),
            _make_attack("ATK-THOR-01", "thor", "CLM-02"),
        ])
        run.defences.extend([
            _make_defence("DEF-THOR-01", "ATK-LOKI-01"),
            _make_defence("DEF-LOKI-01", "ATK-THOR-01"),
        ])
        assert is_debate_converged(run)

    def test_converged_with_no_attacks_both_sides_all_attacked_status(self):
        """If both sides have claims marked 'attacked' but no actual attacks existed, converged."""
        run = RunRecord(run_no=1)
        run.claims.extend([
            _make_claim("CLM-01", "thor", status="attacked"),
            _make_claim("CLM-02", "loki", status="attacked"),
        ])
        # No attacks → attack_ids is empty → empty set is subset of any set → True
        # No submitted claims → True
        assert is_debate_converged(run)

    def test_not_converged_with_partial_defences(self):
        """Only some attacks defended → debate not converged."""
        run = RunRecord(run_no=1)
        run.claims.extend([
            _make_claim("CLM-01", "thor", status="attacked"),
            _make_claim("CLM-02", "loki", status="attacked"),
        ])
        run.attacks.extend([
            _make_attack("ATK-01", "loki", "CLM-01"),
            _make_attack("ATK-02", "thor", "CLM-02"),
        ])
        # Only ATK-01 is defended, ATK-02 is not
        run.defences.append(_make_defence("DEF-01", "ATK-01"))
        assert not is_debate_converged(run)


# ===========================================================================
# DebateTerminationState Tests
# ===========================================================================

class TestDebateTerminationState:
    def test_converged_state_construction(self):
        ts = DebateTerminationState(
            reason=DebateTerminationReason.CONVERGED,
            final_fingerprint="abc123deadbeef01",
            total_turns=6,
            wall_seconds=42.3,
            annotation="Both sides converged.",
        )
        assert ts.reason == DebateTerminationReason.CONVERGED
        assert ts.budget_hit is None
        assert ts.total_turns == 6

    def test_stalled_state_construction(self):
        ts = DebateTerminationState(
            reason=DebateTerminationReason.STALLED,
            final_fingerprint="deadbeef00000001",
            total_turns=12,
            wall_seconds=88.0,
            annotation="No new state in 2 cycles.",
        )
        assert ts.reason == DebateTerminationReason.STALLED
        assert ts.budget_hit is None

    def test_limit_hit_state_construction(self):
        ts = DebateTerminationState(
            reason=DebateTerminationReason.LIMIT_HIT,
            budget_hit="max_debate_turns",
            total_turns=12,
            wall_seconds=180.0,
            annotation="max_debate_turns=12 reached.",
        )
        assert ts.reason == DebateTerminationReason.LIMIT_HIT
        assert ts.budget_hit == "max_debate_turns"

    def test_closed_incomplete_state(self):
        ts = DebateTerminationState(
            reason=DebateTerminationReason.CLOSED_INCOMPLETE,
            annotation="Closed without full evidence.",
        )
        assert ts.reason == DebateTerminationReason.CLOSED_INCOMPLETE

    def test_termination_json_serializable(self):
        ts = DebateTerminationState(
            reason=DebateTerminationReason.CONVERGED,
            total_turns=4,
            wall_seconds=30.1,
            annotation="Converged.",
            closed_at=datetime.now(timezone.utc),
        )
        data = ts.model_dump(mode="json")
        assert data["reason"] == "converged"
        assert data["total_turns"] == 4


# ===========================================================================
# CaseFile Integration Tests
# ===========================================================================

class TestCaseFileIntegration:
    def test_casefile_has_default_debate_budget(self):
        case = _make_case()
        assert isinstance(case.budget, DebateBudget)
        assert case.budget.max_debate_turns == 12
        assert case.budget.turns_used == 0

    def test_casefile_termination_initially_none(self):
        case = _make_case()
        assert case.termination is None

    def test_casefile_budget_can_be_overridden(self):
        case = CaseFile(
            case_id="CASE-OVR",
            question="Test override",
            as_of=date(2027, 1, 25),
            runs=[],
            budget=DebateBudget(max_debate_turns=6, max_wall_seconds=120.0),
        )
        assert case.budget.max_debate_turns == 6
        assert case.budget.max_wall_seconds == 120.0

    def test_casefile_accepts_termination_state(self):
        case = _make_case()
        case.termination = DebateTerminationState(
            reason=DebateTerminationReason.LIMIT_HIT,
            budget_hit="max_debate_turns",
            total_turns=12,
            annotation="Budget hit.",
        )
        assert case.termination.reason == DebateTerminationReason.LIMIT_HIT

    def test_casefile_status_debate_stalled(self):
        case = _make_case()
        case.status = CaseStatus.DEBATE_STALLED
        assert case.status == CaseStatus.DEBATE_STALLED

    def test_casefile_status_debate_limit_hit(self):
        case = _make_case()
        case.status = CaseStatus.DEBATE_LIMIT_HIT
        assert case.status == CaseStatus.DEBATE_LIMIT_HIT

    def test_run_record_has_debate_turns(self):
        run = RunRecord(run_no=1)
        assert run.debate_turns == []

    def test_run_record_accepts_debate_turn_log(self):
        run = RunRecord(run_no=1)
        turn = DebateTurnRecord(
            turn_no=1,
            cycle_no=1,
            phase=DebatePhase.CLAIM_SYNTHESIS,
            agent="thor",
            action="claims_submitted",
            claims_count=2,
        )
        run.debate_turns.append(turn)
        assert len(run.debate_turns) == 1
        assert run.debate_turns[0].agent == "thor"

    def test_casefile_limits_dict_backward_compat(self):
        """Legacy 'limits' dict still accessible for backward-compat code."""
        case = _make_case()
        assert "tool_calls_used" in case.limits
        assert "tokens_used" in case.limits
        # max_rounds and max_runs are REMOVED
        assert "max_rounds" not in case.limits
        assert "max_runs" not in case.limits


# ===========================================================================
# DebateTurnRecord Tests
# ===========================================================================

class TestDebateTurnRecord:
    def test_turn_record_construction(self):
        turn = DebateTurnRecord(
            turn_no=3,
            cycle_no=2,
            phase=DebatePhase.CROSS_EXAMINATION,
            agent="loki",
            action="attacks_submitted",
            attacks_count=2,
            fingerprint_before="abc0000000000001",
            fingerprint_after="def1111111111111",
        )
        assert turn.turn_no == 3
        assert turn.cycle_no == 2
        assert turn.phase == DebatePhase.CROSS_EXAMINATION
        assert turn.agent == "loki"
        assert turn.attacks_count == 2

    def test_turn_record_default_counts_zero(self):
        turn = DebateTurnRecord(
            turn_no=1,
            cycle_no=1,
            phase=DebatePhase.CLAIM_SYNTHESIS,
            agent="thor",
            action="claims_submitted",
        )
        assert turn.claims_count == 0
        assert turn.attacks_count == 0
        assert turn.defences_count == 0
        assert turn.concessions_count == 0

    def test_debate_phase_enum_values(self):
        assert DebatePhase.CLAIM_SYNTHESIS == "claim_synthesis"
        assert DebatePhase.CROSS_EXAMINATION == "cross_examination"
        assert DebatePhase.REBUTTAL == "rebuttal"
        assert DebatePhase.CONCESSION == "concession"


# ===========================================================================
# Safety Budget Scenario Tests
# ===========================================================================

class TestSafetyBudgetScenarios:
    def test_budget_correctly_tracks_turn_increments(self):
        budget = DebateBudget(max_debate_turns=4)
        for i in range(4):
            budget.turns_used += 1
        assert budget.is_any_limit_hit()

    def test_budget_detects_stall_after_stable_cycles(self):
        budget = DebateBudget(max_stable_cycles=2)
        budget.stable_cycles = 1
        assert not budget.is_stalled()
        budget.stable_cycles = 2
        assert budget.is_stalled()

    def test_budget_resets_stable_cycles_on_new_state(self):
        """Simulates runner resetting stable_cycles when state changes."""
        budget = DebateBudget(max_stable_cycles=2)
        budget.stable_cycles = 1
        # New state detected → runner resets
        budget.stable_cycles = 0
        assert not budget.is_stalled()

    def test_budget_no_progress_stall(self):
        budget = DebateBudget(max_no_progress_cycles=3)
        budget.no_progress_cycles = 3
        assert budget.is_stalled()

    def test_budget_no_progress_resets_on_progress(self):
        """Simulates runner resetting no_progress_cycles when new items appear."""
        budget = DebateBudget(max_no_progress_cycles=3)
        budget.no_progress_cycles = 2
        # New item detected → runner resets
        budget.no_progress_cycles = 0
        assert not budget.is_stalled()

    def test_multiple_limits_any_triggers(self):
        """If any single limit is hit, is_any_limit_hit() returns True."""
        budget = DebateBudget(
            max_debate_turns=10,
            max_tool_calls=10,
            max_tokens=10_000,
            max_wall_seconds=120.0,
        )
        budget.tool_calls_used = 10  # only tool_calls hit
        budget.turns_used = 5        # turns not hit
        assert budget.is_any_limit_hit()

    def test_termination_reason_enum_values(self):
        assert DebateTerminationReason.CONVERGED == "converged"
        assert DebateTerminationReason.STALLED == "stalled"
        assert DebateTerminationReason.LIMIT_HIT == "limit_hit"
        assert DebateTerminationReason.CLOSED_INCOMPLETE == "closed_incomplete"
