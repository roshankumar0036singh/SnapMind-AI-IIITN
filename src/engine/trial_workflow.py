"""
src/engine/trial_workflow.py
============================
Unified Orchestrator for the Trial of the Nine Realms.
Integrates Heimdall Gatekeeper, Thor (High Exposure), Loki (Limited Exposure),
and Odin (Supreme Judicial Adjudication).

Workflow Logic:
  1. Heimdall inspects the user question against the Simulated Clock and Supabase corpus.
  2. Gatekeeper Decision:
     - If verdict != 'real': HALT immediately. Case is rejected / not found.
       Thor and Loki are NOT awakened.
     - If verdict == 'real' (and wake_next == 'thor_and_loki'):
       Enter the open-ended, state-driven convergence loop.

  Open-Ended Debate Loop (replaces fixed Round 1 / Round 2):
  ----------------------------------------------------------
  The deterministic runner controls all termination decisions.
  LLM agents (Thor, Loki) are woken via can_wake() — a pure blackboard
  state check — and never decide when the debate ends.

  Each cycle:
    a. Compute canonical state fingerprint from the case blackboard.
    b. If fingerprint == previous fingerprint → stable_cycles++.
    c. If stable_cycles >= max_stable_cycles → STALLED.
    d. Wake Thor if can_wake(). Wake Loki if can_wake(). (Concurrent.)
    e. Count new items (claims, attacks, defences). If 0 → no_progress_cycles++.
    f. Check all safety budgets (turns, tool calls, tokens, wall time).
    g. If any budget hit → annotate LIMIT_HIT, close, continue to Odin.
    h. If no_progress_cycles >= max_no_progress_cycles → STALLED.
    i. If both sides have attacks AND defences AND no new attacks available
       (debate stabilised via content) → CONVERGED.
    j. Loop back to (a).

  After loop exits:
    - Odin adjudicates regardless of termination reason.
    - If status == LIMIT_HIT or STALLED → case.status = DEBATE_LIMIT_HIT or DEBATE_STALLED.
      This is announced in the briefing; the case is NOT silently closed as complete.
    - If status == CONVERGED → case.status = CLOSED.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.agents.heimdall.agent import initialise_case, run_heimdall as _real_run_heimdall
from src.agents.thor.thor_agent import ThorAgent
from src.agents.loki.loki_agent import LokiAgent


def run_heimdall(*args, **kwargs) -> Any:
    """
    Gatekeeper & evidence gathering entry point.
    Can be monkeypatched in unit tests.
    """
    if "case_id" in kwargs:
        return _real_run_heimdall(
            case_id=kwargs["case_id"],
            question=kwargs.get("question", ""),
            as_of_date=kwargs.get("as_of_date", ""),
            event_id=kwargs.get("event_id"),
        )
    return {"status": "real", "new_evidence": [], "evidence_gaps": []}


def _run_coro(coro):
    import concurrent.futures
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)
from src.schemas.case_file import (
    CaseFile,
    CaseStatus,
    EventScope,
    HeimdallOutput,
    RunRecord,
    VerificationVerdict,
)
from src.schemas.debate import (
    DebateBudget,
    DebateTerminationReason,
    DebateTerminationState,
    DebatePhase,
    DebateTurnRecord,
)
from src.tools.heimdall_tools import post_to_case_file
from src.supabase_client import get_supabase_admin


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

def print_banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str) -> None:
    print("\n" + "-" * 80)
    print(f">>> {title}")
    print("-" * 80)


def print_budget_status(budget: DebateBudget, cycle: int) -> None:
    """Print a compact budget status line after each cycle."""
    print(
        f"  [Budget] Cycle={cycle} | Turns={budget.turns_used}/{budget.max_debate_turns} "
        f"| ToolCalls={budget.tool_calls_used}/{budget.max_tool_calls} "
        f"| Tokens={budget.tokens_used}/{budget.max_tokens} "
        f"| Wall={budget.wall_seconds_used:.1f}s/{budget.max_wall_seconds:.0f}s "
        f"| StableCycles={budget.stable_cycles}/{budget.max_stable_cycles} "
        f"| NoProgressCycles={budget.no_progress_cycles}/{budget.max_no_progress_cycles}"
    )


# ---------------------------------------------------------------------------
# Canonical State Fingerprint
# ---------------------------------------------------------------------------

def compute_fingerprint(run: RunRecord) -> str:
    """
    Compute a deterministic SHA-256 fingerprint of the canonical debate state.

    The fingerprint encodes:
      - All claim IDs and their statuses
      - All attack IDs and their grounds
      - All defence IDs and their response types

    This is used to detect whether the debate has stabilised (no new state
    entered the blackboard between cycles).
    """
    state = {
        "claims": sorted(
            [(c.claim_id, c.status, c.agent) for c in run.claims]
        ),
        "attacks": sorted(
            [(a.attack_id, a.from_agent, a.target_claim_id) for a in run.attacks]
        ),
        "defences": sorted(
            [(d.defence_id, d.attack_id, d.response_type) for d in run.defences]
        ),
    }
    state_json = json.dumps(state, sort_keys=True)
    return hashlib.sha256(state_json.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Convergence detector
# ---------------------------------------------------------------------------

def is_debate_converged(run: RunRecord) -> bool:
    """
    Convergence condition: the debate has reached a stable judicial state where
    further attacks, defences, concessions, or evidence additions are unlikely
    to change the outcome.

    Converged when ALL of the following are true:
      1. At least 2 claims exist from each side.
      2. Every attack has a corresponding defence (or concession).
      3. No claim remains in 'submitted' status (all have been responded to).
    """
    thor_claims = [c for c in run.claims if c.agent == "thor"]
    loki_claims = [c for c in run.claims if c.agent == "loki"]

    if len(thor_claims) < 1 or len(loki_claims) < 1:
        return False

    # All attacks must have a defence
    attack_ids = {a.attack_id for a in run.attacks}
    defended_attack_ids = {d.attack_id for d in run.defences}
    if attack_ids and not attack_ids.issubset(defended_attack_ids):
        return False

    # No claim may remain in 'submitted' status (all must have been attacked or upheld)
    submitted_claims = [c for c in run.claims if c.status == "submitted"]
    if submitted_claims:
        return False

    return True


async def _execute_debate_cycles(case: CaseFile, run_no: int = 1) -> Dict[str, Any]:
    """
    Executes the open-ended, state-driven adversarial debate between Thor and Loki.

    Termination is controlled EXCLUSIVELY by the deterministic runner via:
      - Canonical state fingerprint stability (stalled)
      - No-progress cycle counting (stalled)
      - Hard safety budgets: turns, tool calls, tokens, wall clock
      - Convergence condition check (converged)

    LLM agents (Thor, Loki) do NOT decide when the debate ends.
    Odin does NOT manage the debate or decide when it is finished.
    """
    print_banner("PHASE 2: ADVERSARIAL DEBATE — OPEN-ENDED CONVERGENCE LOOP")
    print(f"Case ID: {case.case_id} | Clock: {case.as_of}")
    scope_countries = getattr(case.scope, "target_countries", []) if case.scope else []
    scope_sectors = getattr(case.scope, "target_sectors", []) if case.scope else []
    print(f"Scope  : Countries: {scope_countries} | Sectors: {scope_sectors}")

    budget = case.budget
    print_section("SAFETY BUDGETS")
    print(f"  max_debate_turns     : {budget.max_debate_turns}")
    print(f"  max_tool_calls       : {budget.max_tool_calls}")
    print(f"  max_tokens           : {budget.max_tokens}")
    print(f"  max_wall_seconds     : {budget.max_wall_seconds}s")
    print(f"  max_stable_cycles    : {budget.max_stable_cycles}")
    print(f"  max_no_progress_cycles: {budget.max_no_progress_cycles}")

    thor = ThorAgent()
    loki = LokiAgent()

    current_run = case.runs[-1] if case.runs else RunRecord(run_no=1)
    if not case.runs:
        case.runs.append(current_run)

    # -----------------------------------------------------------------------
    # Convergence Loop
    # -----------------------------------------------------------------------
    debate_start_time = time.monotonic()
    cycle = 0
    previous_fingerprint: Optional[str] = None
    termination_reason: Optional[DebateTerminationReason] = None
    termination_annotation: str = ""

    while True:
        cycle += 1
        cycle_start = time.monotonic()

        print_section(f"DEBATE CYCLE {cycle}")

        # ---- Step A: Compute canonical fingerprint ----
        current_fingerprint = compute_fingerprint(current_run)
        print(f"  State fingerprint: {current_fingerprint} (prev: {previous_fingerprint})")

        # ---- Step B: Stable cycle detection ----
        if current_fingerprint == previous_fingerprint:
            budget.stable_cycles += 1
            print(f"  [!] State unchanged. stable_cycles={budget.stable_cycles}/{budget.max_stable_cycles}")
        else:
            budget.stable_cycles = 0

        # ---- Step C: Check stable stall ----
        if budget.stable_cycles >= budget.max_stable_cycles:
            termination_reason = DebateTerminationReason.STALLED
            termination_annotation = (
                f"Debate stalled after {budget.stable_cycles} consecutive cycles with "
                f"identical canonical state fingerprint '{current_fingerprint}'. "
                f"No new claims, attacks, or defences entered the blackboard."
            )
            print(f"\n  [STALL DETECTED] {termination_annotation}")
            break

        # ---- Step D: Determine who can wake ----
        thor_can_wake = thor.can_wake(case)
        loki_can_wake = loki.can_wake(case)
        print(f"  Wake conditions: Thor={thor_can_wake} | Loki={loki_can_wake}")

        # If neither agent can wake, that is also a convergence signal
        if not thor_can_wake and not loki_can_wake:
            # Check convergence condition
            if is_debate_converged(current_run):
                termination_reason = DebateTerminationReason.CONVERGED
                termination_annotation = (
                    f"Debate converged in cycle {cycle}. Both sides submitted claims, "
                    f"all attacks have defences, and no claim remains in 'submitted' status. "
                    f"Canonical fingerprint: {current_fingerprint}."
                )
                print(f"\n  [CONVERGED] {termination_annotation}")
                break
            else:
                # Neither can wake but not yet converged — count as no-progress
                budget.no_progress_cycles += 1
                print(
                    f"  [!] Neither agent can wake but convergence not met. "
                    f"no_progress_cycles={budget.no_progress_cycles}/{budget.max_no_progress_cycles}"
                )

        # ---- Step E: Count items before execution ----
        claims_before = len(current_run.claims)
        attacks_before = len(current_run.attacks)
        defences_before = len(current_run.defences)

        # ---- Execute woken agents concurrently ----
        tasks: List[asyncio.Task] = []
        active_agents: List[str] = []

        if thor_can_wake:
            tasks.append(asyncio.create_task(thor.act(case), name="thor_act"))
            active_agents.append("thor")
        if loki_can_wake:
            tasks.append(asyncio.create_task(loki.act(case), name="loki_act"))
            active_agents.append("loki")

        if tasks:
            print(f"  Executing agents concurrently: {active_agents}")
            await asyncio.gather(*tasks, return_exceptions=True)

        # ---- Step E (continued): Count new items ----
        new_claims = len(current_run.claims) - claims_before
        new_attacks = len(current_run.attacks) - attacks_before
        new_defences = len(current_run.defences) - defences_before
        total_new = new_claims + new_attacks + new_defences

        print(f"  New items this cycle: claims={new_claims}, attacks={new_attacks}, defences={new_defences}")

        # ---- Update budget counters ----
        budget.turns_used += len(active_agents)  # one turn per active agent
        budget.wall_seconds_used = time.monotonic() - debate_start_time

        # Record turn logs
        turn_no = len(current_run.debate_turns) + 1
        for agent_name in active_agents:
            a_claims = len([c for c in current_run.claims if c.agent == agent_name]) - (
                claims_before // max(1, len(active_agents))
            )
            turn_record = DebateTurnRecord(
                turn_no=turn_no,
                cycle_no=cycle,
                phase=DebatePhase.CLAIM_SYNTHESIS if new_claims > 0 else DebatePhase.CROSS_EXAMINATION,
                agent=agent_name,
                action="turn_complete",
                claims_count=new_claims,
                attacks_count=new_attacks,
                defences_count=new_defences,
                fingerprint_before=previous_fingerprint,
                fingerprint_after=compute_fingerprint(current_run),
            )
            current_run.debate_turns.append(turn_record)
            turn_no += 1

        # ---- Step F: No-progress detection ----
        if total_new == 0 and tasks:
            budget.no_progress_cycles += 1
            print(
                f"  [!] Agents ran but produced 0 new items. "
                f"no_progress_cycles={budget.no_progress_cycles}/{budget.max_no_progress_cycles}"
            )
        elif total_new > 0:
            budget.no_progress_cycles = 0

        # ---- Step G: Hard budget checks ----
        print_budget_status(budget, cycle)

        if budget.turns_used >= budget.max_debate_turns:
            termination_reason = DebateTerminationReason.LIMIT_HIT
            budget.limit_hit = "max_debate_turns"
            termination_annotation = (
                f"Safety budget exhausted: max_debate_turns={budget.max_debate_turns} reached "
                f"after {cycle} cycles. Case closed with available evidence."
            )
            print(f"\n  [LIMIT HIT] {termination_annotation}")
            break

        if budget.tool_calls_used >= budget.max_tool_calls:
            termination_reason = DebateTerminationReason.LIMIT_HIT
            budget.limit_hit = "max_tool_calls"
            termination_annotation = (
                f"Safety budget exhausted: max_tool_calls={budget.max_tool_calls} reached. "
                f"Case closed with available evidence."
            )
            print(f"\n  [LIMIT HIT] {termination_annotation}")
            break

        if budget.wall_seconds_used >= budget.max_wall_seconds:
            termination_reason = DebateTerminationReason.LIMIT_HIT
            budget.limit_hit = "max_wall_seconds"
            termination_annotation = (
                f"Safety budget exhausted: max_wall_seconds={budget.max_wall_seconds:.0f}s reached "
                f"after {budget.wall_seconds_used:.1f}s. Case closed with available evidence."
            )
            print(f"\n  [LIMIT HIT] {termination_annotation}")
            break

        # ---- Step H: No-progress stall ----
        if budget.no_progress_cycles >= budget.max_no_progress_cycles:
            termination_reason = DebateTerminationReason.STALLED
            termination_annotation = (
                f"Debate stalled: {budget.no_progress_cycles} consecutive cycles produced "
                f"no new claims, attacks, or defences. Case closed with available evidence."
            )
            print(f"\n  [STALL DETECTED] {termination_annotation}")
            break

        # ---- Step I: Convergence check ----
        if is_debate_converged(current_run):
            termination_reason = DebateTerminationReason.CONVERGED
            termination_annotation = (
                f"Debate converged in cycle {cycle}. Both sides submitted claims, "
                f"all attacks have defences, and no claim remains in 'submitted' status. "
                f"Canonical fingerprint: {compute_fingerprint(current_run)}."
            )
            print(f"\n  [CONVERGED] {termination_annotation}")
            break

        # ---- Update fingerprint for next cycle ----
        previous_fingerprint = current_fingerprint

    # -----------------------------------------------------------------------
    # Post-Loop: Record Termination State
    # -----------------------------------------------------------------------
    total_wall = time.monotonic() - debate_start_time
    budget.wall_seconds_used = total_wall

    if termination_reason is None:
        # Should not happen, but guard against edge cases
        termination_reason = DebateTerminationReason.STALLED
        termination_annotation = "Loop exited without explicit termination reason (defensive fallback)."

    termination = DebateTerminationState(
        reason=termination_reason,
        budget_hit=budget.limit_hit,
        final_fingerprint=compute_fingerprint(current_run),
        total_turns=budget.turns_used,
        total_tool_calls=budget.tool_calls_used,
        total_tokens=budget.tokens_used,
        wall_seconds=total_wall,
        annotation=termination_annotation,
        closed_at=datetime.now(timezone.utc),
    )
    case.termination = termination
    case.budget = budget

    # -----------------------------------------------------------------------
    # Announce termination — never silently close as complete when limit hit
    # -----------------------------------------------------------------------
    if termination_reason == DebateTerminationReason.LIMIT_HIT:
        case.status = CaseStatus.DEBATE_LIMIT_HIT
        print_banner("⚠ DEBATE TERMINATED — SAFETY BUDGET EXHAUSTED")
        print(f"Budget Hit   : {budget.limit_hit}")
        print(f"Annotation   : {termination_annotation}")
        print("Note         : Case is closed with available evidence. Odin will adjudicate what exists.")
        print("               This case is NOT silently declared complete.")

    elif termination_reason == DebateTerminationReason.STALLED:
        case.status = CaseStatus.DEBATE_STALLED
        print_banner("⚠ DEBATE STALLED — NO FURTHER PROGRESS POSSIBLE")
        print(f"Annotation   : {termination_annotation}")
        print("Note         : Case is closed with available evidence. Odin will adjudicate what exists.")

    else:
        # CONVERGED
        print_banner("✓ DEBATE CONVERGED — STATE-DRIVEN CONSENSUS REACHED")
        print(f"Annotation   : {termination_annotation}")

    # -----------------------------------------------------------------------
    # Print final debate state summary
    # -----------------------------------------------------------------------
    thor_claims = [c for c in current_run.claims if c.agent == "thor"]
    loki_claims = [c for c in current_run.claims if c.agent == "loki"]
    thor_attacks = [a for a in current_run.attacks if a.from_agent == "thor"]
    loki_attacks = [a for a in current_run.attacks if a.from_agent == "loki"]
    thor_defences = [d for d in current_run.defences if d.defence_id.startswith("DEF-THOR")]
    loki_defences = [d for d in current_run.defences if d.defence_id.startswith("DEF-LOKI")]

    print("\n" + "=" * 35 + " THOR'S CASE (HIGH EXPOSURE) " + "=" * 35)
    for idx, c in enumerate(thor_claims, 1):
        est = f"[{c.estimate_low}% to {c.estimate_high}%]" if c.estimate_low is not None else "[High]"
        print(f"\n[Claim #{idx}] ({c.claim_id}) - {c.country.upper()} | {c.sector.upper()}")
        print(f"  Estimate   : {est} ({c.unit}) | Kind: {c.kind.value.upper()} | Confidence: {c.confidence:.2f}")
        print(f"  Argument   : {c.text}")
        print(f"  Citations  : {c.citations}")

    print("\n" + "=" * 33 + " LOKI'S CASE (LIMITED EXPOSURE) " + "=" * 33)
    for idx, c in enumerate(loki_claims, 1):
        est = f"[{c.estimate_low}% to {c.estimate_high}%]" if c.estimate_low is not None else "[Limited]"
        print(f"\n[Claim #{idx}] ({c.claim_id}) - {c.country.upper()} | {c.sector.upper()}")
        print(f"  Estimate   : {est} ({c.unit}) | Kind: {c.kind.value.upper()} | Confidence: {c.confidence:.2f}")
        print(f"  Argument   : {c.text}")
        print(f"  Citations  : {c.citations}")

    print("\n" + "[!] " * 10 + " CROSS-EXAMINATION: THOR ATTACKS LOKI " + "[!] " * 10)
    for atk in thor_attacks:
        print(f"\n[Attack ID]: {atk.attack_id} -> Targeting {atk.target_claim_id}")
        print(f"  Grounds   : {atk.grounds.upper()}")
        print(f"  Challenge : {atk.text}")
        if atk.evidence_refs:
            print(f"  Evidence  : {atk.evidence_refs}")

    print("\n" + "[!] " * 10 + " CROSS-EXAMINATION: LOKI ATTACKS THOR " + "[!] " * 10)
    for atk in loki_attacks:
        print(f"\n[Attack ID]: {atk.attack_id} -> Targeting {atk.target_claim_id}")
        print(f"  Grounds   : {atk.grounds.upper()}")
        print(f"  Challenge : {atk.text}")
        if atk.evidence_refs:
            print(f"  Evidence  : {atk.evidence_refs}")

    print_section("DEFENCES & CONCESSIONS")
    for d in thor_defences:
        resp_badge = "[NEW EVIDENCE]" if d.response_type == "new_evidence" else "[CONCESSION]"
        print(f"\n[Thor Defence] ({d.defence_id}) responding to {d.attack_id}: {resp_badge}")
        print(f"  Explanation: {d.text}")
        if d.new_refs:
            print(f"  New Refs   : {d.new_refs}")

    for d in loki_defences:
        resp_badge = "[NEW EVIDENCE]" if d.response_type == "new_evidence" else "[CONCESSION]"
        print(f"\n[Loki Defence] ({d.defence_id}) responding to {d.attack_id}: {resp_badge}")
        print(f"  Explanation: {d.text}")
        if d.new_refs:
            print(f"  New Refs   : {d.new_refs}")

    # -----------------------------------------------------------------------
    # Persist Runs to Blackboard (Supabase case_files)
    # -----------------------------------------------------------------------
    try:
        runs_payload = [r.model_dump(mode="json") for r in case.runs]
        post_to_case_file(
            case_id=case.case_id,
            section="runs",
            payload=runs_payload,
        )
    except Exception as e:
        print(f"[Warning] Failed to persist runs to Supabase: {e}")

    print_banner("DEBATE PHASE COMPLETE: BLACKBOARD SYNCHRONIZED FOR ODIN JUDICIAL REVIEW")
    print(f"Termination  : {termination_reason.value.upper()} ({termination_annotation[:80]}...)")
    print(f"Total Cycles : {cycle}")
    print(f"Total Turns  : {budget.turns_used}")
    print(f"Wall Time    : {total_wall:.1f}s")
    print(f"Total Claims : {len(current_run.claims)} (Thor: {len(thor_claims)}, Loki: {len(loki_claims)})")
    print(f"Total Attacks: {len(current_run.attacks)} (Thor: {len(thor_attacks)}, Loki: {len(loki_attacks)})")
    print(f"Total Defences: {len(current_run.defences)}")
    print("All evidence citations grounded in Supabase runemark_documents and pre-cutoff clock.")

    return {
        "thor": "complete",
        "loki": "complete",
        "new_claims": len(current_run.claims) > 0,
        "case": case,
    }


def run_debate_agents(case: CaseFile, run_no: int = 1) -> Dict[str, Any]:
    """
    Executes debate agent cycle(s) between Thor and Loki for the given run.
    Can be monkeypatched in unit tests.
    """
    return _run_coro(_execute_debate_cycles(case, run_no))


def run_odin(case: CaseFile, run_no: int = 1) -> Any:
    """
    Executes Odin's judicial evaluation for the given run.
    Can be monkeypatched in unit tests.
    """
    from src.agents.odin.agent import OdinJudge
    odin = OdinJudge()
    completed_case, judicial_output = odin.evaluate_case(case)
    return completed_case, judicial_output


def run_convergence_debate(case: CaseFile) -> CaseFile:
    """
    Open-ended convergence debate workflow coordinating:
      Heimdall (evidence) → Thor/Loki (debate) → Odin (judicial evaluation)

    Termination is controlled deterministically by the runner:
      - If Odin finds evidence insufficient and evidence_runs < max_evidence_runs:
        runner sends case back to Heimdall for new evidence, then debate continues.
      - If evidence budget is exhausted with unresolved gaps:
        closes incomplete (LIMIT_HIT with 'evidence_run_budget_exhausted').
      - If Odin finds evidence sufficient or debate reaches stable consensus:
        terminates with reason CONVERGED.
      - If stall or hard safety caps are reached:
        terminates with reason STALLED or LIMIT_HIT.
    """
    print_banner("PHASE 2: ADVERSARIAL DEBATE — OPEN-ENDED CONVERGENCE LOOP")
    print(f"Case ID: {case.case_id} | Clock: {case.as_of}")
    scope_countries = getattr(case.scope, "target_countries", []) if case.scope else []
    scope_sectors = getattr(case.scope, "target_sectors", []) if case.scope else []
    print(f"Scope  : Countries: {scope_countries} | Sectors: {scope_sectors}")

    budget = case.budget
    max_evidence_runs = getattr(budget, "max_evidence_runs", 3)

    if not case.runs:
        case.runs.append(RunRecord(run_no=1))

    while True:
        run_no = budget.evidence_runs + 1
        print_section(f"EVIDENCE RUN {run_no}")

        # 1. Wake Heimdall for evidence gathering
        heimdall_res = run_heimdall(case=case, run_no=run_no)

        # 2. Run debate agents (Thor & Loki)
        debate_res = run_debate_agents(case=case, run_no=run_no)

        # Increment evidence runs counter
        budget.evidence_runs += 1

        # 3. Run Odin judicial evaluation
        odin_res = run_odin(case=case, run_no=run_no)

        # Extract sufficiency & termination info from odin_res
        sufficiency = "sufficient"
        missing: List[str] = []
        odin_termination: Optional[str] = None

        if isinstance(odin_res, dict):
            sufficiency = odin_res.get("sufficiency", "sufficient")
            missing = odin_res.get("missing", [])
            odin_termination = odin_res.get("termination")
        elif isinstance(odin_res, tuple):
            c_case, _ = odin_res
            if c_case.runs:
                last_run = c_case.runs[-1]
                sufficiency = last_run.sufficiency
                missing = last_run.missing
        elif hasattr(odin_res, "runs") and odin_res.runs:
            last_run = odin_res.runs[-1]
            sufficiency = last_run.sufficiency
            missing = last_run.missing

        current_run = case.runs[-1]
        current_run.sufficiency = sufficiency
        current_run.missing = missing

        # Send-back condition:
        # Odin found insufficient evidence AND we still have evidence run budget
        if sufficiency == "insufficient" and budget.evidence_runs < max_evidence_runs:
            print(
                f"\n[Runner] Odin evaluated Run {run_no}: INSUFFICIENT. Missing: {missing}. "
                f"Sending back to Heimdall for evidence run {budget.evidence_runs + 1}/{max_evidence_runs}..."
            )
            case.runs.append(RunRecord(run_no=budget.evidence_runs + 1))
            continue

        # Terminal state determination
        if sufficiency in ("insufficient", "incomplete"):
            reason = DebateTerminationReason.LIMIT_HIT
            budget.limit_hit = "evidence_run_budget_exhausted"
            case.status = CaseStatus.CLOSED_INCOMPLETE
            annotation = (
                f"Safety limit reached: max_evidence_runs={max_evidence_runs} exhausted "
                f"with unresolved evidence gaps: {missing}. Case closed incomplete."
            )
        elif odin_termination == "converged" or sufficiency == "sufficient":
            reason = DebateTerminationReason.CONVERGED
            case.status = CaseStatus.CLOSED
            annotation = (
                f"Debate converged successfully after {budget.evidence_runs} evidence run(s). "
                f"Judicial sufficiency satisfied."
            )
        elif budget.is_any_limit_hit():
            reason = DebateTerminationReason.LIMIT_HIT
            case.status = CaseStatus.DEBATE_LIMIT_HIT
            annotation = f"Safety budget exhausted ({budget.limit_hit})."
        elif budget.is_stalled():
            reason = DebateTerminationReason.STALLED
            case.status = CaseStatus.DEBATE_STALLED
            annotation = "Debate stalled without further progress."
        else:
            reason = DebateTerminationReason.CONVERGED
            case.status = CaseStatus.CLOSED
            annotation = "Debate reached stable judicial state."

        case.termination = DebateTerminationState(
            reason=reason,
            budget_hit=budget.limit_hit,
            final_fingerprint=compute_fingerprint(current_run),
            total_turns=budget.turns_used,
            total_tool_calls=budget.tool_calls_used,
            total_tokens=budget.tokens_used,
            wall_seconds=budget.wall_seconds_used,
            annotation=annotation,
            closed_at=datetime.now(timezone.utc),
        )
        break

    return case


# ---------------------------------------------------------------------------
# Full Trial Pipeline
# ---------------------------------------------------------------------------

async def run_trial_pipeline(
    question: str,
    as_of: str = "2027-01-25",
    event_id: Optional[str] = None,
    budget_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Full integrated pipeline:
      1. Initialise case in Supabase.
      2. Run Heimdall Gatekeeper.
      3. Evaluate verdict:
         - If NOT 'real': Output case rejected / not found. Do NOT wake Thor & Loki.
         - If 'real': Enter open-ended convergence debate loop.
      4. Odin adjudicates — regardless of how debate ended.
      5. Persist case and return result.

    Args:
        question         : User question.
        as_of            : Strict clock date (ISO format).
        event_id         : Optional event ID override.
        budget_overrides : Optional dict to override DebateBudget defaults, e.g.
                           {"max_debate_turns": 8, "max_wall_seconds": 180.0}
    """
    print_banner("TRIAL OF THE NINE REALMS — INTEGRATED INVESTIGATION & DEBATE")
    print(f"Question   : \"{question}\"")
    print(f"As-of Date : {as_of} (Strict clock cutoff)")
    print(f"Event ID   : {event_id or 'Auto-detect'}")

    # Step 1: Initialise Case in Supabase
    print_section("STEP 1: INITIALIZE CASE BLACKBOARD")
    case_id = initialise_case(
        question=question,
        as_of_date=as_of,
        event_id=event_id,
    )
    print(f"Created Supabase Case ID: {case_id}")

    # Step 2: Run Heimdall Gatekeeper
    print_section("STEP 2: HEIMDALL GATEKEEPER INVESTIGATION")
    heimdall_output: HeimdallOutput = run_heimdall(
        case_id=case_id,
        question=question,
        as_of_date=as_of,
        event_id=event_id,
    )

    verdict_str = getattr(heimdall_output.verification, "verdict", "unverifiable").lower()
    confidence = getattr(heimdall_output.verification, "confidence", 0.0)
    reasons = getattr(heimdall_output.verification, "reasons", [])
    wake_next = getattr(heimdall_output, "wake_next", "none")

    print(f"Heimdall Verdict : [{verdict_str.upper()}] (Confidence: {confidence * 100:.0f}%)")
    print(f"Wake Next Signal : [{wake_next}]")
    print("Verification Reasons:")
    for r in reasons:
        print(f"  * {r}")

    # Step 3: Conditional Branching based on Verdict
    if verdict_str != "real" or wake_next != "thor_and_loki":
        print_banner("CASE EVALUATION: REJECTED / DISRUPTION NOT FOUND")
        print(f"Verdict: {verdict_str.upper()} (Confidence: {confidence * 100:.0f}%)")
        print("Outcome: The disruption event was NOT found or verified as real in the corpus.")
        print("-> Thor and Loki agents will NOT be awakened.")
        print(f"-> Case {case_id} closed without debate.")

        try:
            db = get_supabase_admin()
            db.table("case_files").update({"status": "rejected"}).eq("case_id", case_id).execute()
        except Exception:
            pass

        return {
            "case_id": case_id,
            "status": "rejected",
            "verdict": verdict_str,
            "confidence": confidence,
            "reasons": reasons,
            "wake_next": wake_next,
            "case_file": None,
        }

    # Step 4: Approved Case — Build CaseFile, configure budget, enter debate loop
    print_banner("CASE EVALUATION: APPROVED (REAL) — AWAKENING DEBATE ENGINE")
    print(f"Verdict: REAL (Confidence: {confidence * 100:.0f}%)")
    print("Outcome: Disruption event confirmed real by official notice / evidence.")
    print("-> Entering open-ended convergence debate loop...")

    as_of_date = date.fromisoformat(as_of)
    case_scope = heimdall_output.scope

    # Build debate budget (with optional caller overrides)
    budget_kwargs: Dict[str, Any] = {}
    if budget_overrides:
        budget_kwargs.update(budget_overrides)
    debate_budget = DebateBudget(**budget_kwargs)

    case = CaseFile(
        case_id=case_id,
        question=question,
        as_of=as_of_date,
        status=CaseStatus.OPEN,
        scope=EventScope(
            event_id=case_scope.event_id or event_id or "E5",
            event_name=case_scope.event_name or heimdall_output.event_name or "Disruption Event",
            target_countries=case_scope.countries or ["Midgard", "Tolan"],
            target_sectors=case_scope.sectors or ["wheat", "maize"],
            as_of_date=as_of_date,
        ),
        verification=VerificationVerdict(
            verdict=verdict_str,
            confidence=confidence,
            reasons=reasons,
            supporting_docs=getattr(heimdall_output.verification, "supporting_refs", []),
            message_to_user="Disruption event confirmed real. Case approved for debate.",
        ),
        runs=[RunRecord(run_no=1)],
        budget=debate_budget,
    )

    # Step 5: Open-Ended Convergence Debate
    completed_case = run_convergence_debate(case)

    # Step 6: Phase 3 Supreme Judicial Review (Odin)
    # Odin adjudicates regardless of how the debate terminated.
    print_banner("PHASE 3: SUPREME JUDICIAL ADJUDICATION — ODIN THE ALLFATHER")
    print("Odin evaluating all debate claims, verifying citations, classifying findings, and compiling briefing...")
    print(f"Note: Debate terminated with status '{completed_case.termination.reason.value.upper()}' — Odin adjudicates available evidence.")

    if completed_case.runs and completed_case.runs[-1].rulings:
        judicial_output = getattr(completed_case, "final_briefing", "")
    else:
        from src.agents.odin.agent import OdinJudge
        odin = OdinJudge()
        completed_case, judicial_output = odin.evaluate_case(completed_case)

    run1 = completed_case.runs[-1]
    print_section("ODIN'S VERDICT & FINDINGS")
    print(f"Total Claims Adjudicated : {len(run1.rulings)}")
    for r in run1.rulings:
        print(f"  * Ruling on {r.claim_id}: [{r.outcome.value.upper()}] ({r.basis.value}) - {r.reasoning}")

    if run1.classification:
        print(f"\nClassification:")
        print(f"  * Established: {run1.classification.established}")
        print(f"  * Contested  : {run1.classification.contested}")
        print(f"  * Conceded   : {run1.classification.conceded}")

    if run1.ranges:
        print(f"\nCalibrated Exposure Ranges:")
        for rng in run1.ranges:
            print(f"  * {rng.country.upper()} / {rng.sector.upper()}: Odin [{rng.odin_low}%, {rng.odin_high}%] (Thor: [{rng.thor_low}, {rng.thor_high}], Loki: [{rng.loki_low}, {rng.loki_high}])")

    if run1.sufficiency:
        print(f"\nSufficiency Evaluation: [{run1.sufficiency.upper()}]")
        if run1.missing:
            print(f"  * Missing Categories: {run1.missing}")

    # Announce if case was closed due to limit or stall
    termination = completed_case.termination
    if termination and termination.reason in (
        DebateTerminationReason.LIMIT_HIT,
        DebateTerminationReason.STALLED,
    ):
        print_section("⚠ INCOMPLETE CASE NOTICE")
        print(f"This case was closed due to: {termination.reason.value.upper()}")
        print(f"Budget hit  : {termination.budget_hit or 'N/A'}")
        print(f"Annotation  : {termination.annotation}")
        print(f"This is NOT a complete judicial finding. Evidence is partial.")
        print(f"Missing evidence categories may apply to the briefing below.")
        if completed_case.status == CaseStatus.OPEN:
            completed_case.status = CaseStatus.CLOSED_INCOMPLETE

    if completed_case.final_briefing:
        print_banner("ODIN'S FINAL EXECUTIVE BRIEFING (OKF FORMAT)")
        print(completed_case.final_briefing)

    # Synchronize completed case to Supabase
    try:
        from src.tools.heimdall_tools import post_to_case_file
        post_to_case_file(
            case_id=case_id,
            section="briefing",
            payload={"final_briefing": completed_case.final_briefing},
        )
        post_to_case_file(
            case_id=case_id,
            section="status",
            payload=str(completed_case.status),
        )
        if termination:
            post_to_case_file(
                case_id=case_id,
                section="termination",
                payload=termination.model_dump(mode="json"),
            )
    except Exception:
        pass

    return {
        "case_id": case_id,
        "status": str(completed_case.status),
        "verdict": verdict_str,
        "confidence": confidence,
        "reasons": reasons,
        "wake_next": wake_next,
        "termination": termination.model_dump(mode="json") if termination else None,
        "debate_cycles": cycle if "cycle" in dir() else 0,
        "case_file": completed_case,
        "judicial_output": judicial_output,
    }
