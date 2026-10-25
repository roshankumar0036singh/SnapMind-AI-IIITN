"""
src/engine/trial_workflow.py
============================
Unified Orchestrator for the Trial of the Nine Realms.
Integrates Heimdall Gatekeeper, Thor (High Exposure), and Loki (Limited Exposure).

Workflow Logic:
  1. Heimdall inspects the user question against the Simulated Clock and Supabase corpus.
  2. Gatekeeper Decision:
     - If verdict != 'real': HALT immediately. Case is rejected / not found.
       Thor and Loki are NOT awakened.
     - If verdict == 'real' (and wake_next == 'thor_and_loki'):
       Awaken Thor and Loki concurrently to search Supabase embeddings and debate.
  3. Round 1: Concurrent claim synthesis (Thor argues high exposure; Loki argues limited exposure).
  4. Round 2: Concurrent cross-examination (attacks, counter-evidence, defences).
  5. Blackboard Sync: Persist all claims, attacks, and defences to Supabase case_files.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Dict, List, Optional

from src.agents.heimdall.agent import initialise_case, run_heimdall
from src.agents.thor.thor_agent import ThorAgent
from src.agents.loki.loki_agent import LokiAgent
from src.schemas.case_file import (
    CaseFile,
    CaseStatus,
    EventScope,
    HeimdallOutput,
    RunRecord,
    VerificationVerdict,
)
from src.tools.heimdall_tools import post_to_case_file
from src.supabase_client import get_supabase_admin


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    print("\n" + "-" * 80)
    print(f">>> {title}")
    print("-" * 80)


async def run_thor_and_loki_debate(case: CaseFile) -> CaseFile:
    """
    Executes the concurrent adversarial debate between Thor and Loki.
    Enforces planner-free blackboard wake conditions (NFR1).
    """
    print_banner("PHASE 2: ADVERSARIAL DEBATE -- THOR & LOKI AWAKENED")
    print(f"Case ID: {case.case_id} | Clock: {case.as_of}")
    scope_countries = getattr(case.scope, "target_countries", []) if case.scope else []
    scope_sectors = getattr(case.scope, "target_sectors", []) if case.scope else []
    print(f"Scope  : Countries: {scope_countries} | Sectors: {scope_sectors}")

    thor = ThorAgent()
    loki = LokiAgent()

    # ---------------------------------------------------------------------------
    # Round 1: Concurrent Autonomous Search & Claim Synthesis
    # ---------------------------------------------------------------------------
    print_section("ROUND 1: PARALLEL EMBEDDING SEARCH & CLAIM SYNTHESIS")
    print("Executing Thor and Loki concurrently via asyncio.gather()...")
    print("  * Thor querying Supabase for: closures, blockades, capacity drops, maritime deficits...")
    print("  * Loki querying Supabase for: alternative rail corridors, inventory stockpiles, commercial substitution...")

    thor_r1_task = asyncio.create_task(thor.act(case))
    loki_r1_task = asyncio.create_task(loki.act(case))

    await asyncio.gather(thor_r1_task, loki_r1_task)

    current_run = case.runs[0]
    thor_claims = [c for c in current_run.claims if c.agent == "thor"]
    loki_claims = [c for c in current_run.claims if c.agent == "loki"]

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

    # ---------------------------------------------------------------------------
    # Round 2: Concurrent Cross-Examination (Attacks & Defences)
    # ---------------------------------------------------------------------------
    print_section("ROUND 2: CROSS-EXAMINATION & EVIDENCE-BASED ATTACKS")
    print("Executing Round 2 concurrently via asyncio.gather()...")
    print("  * Thor inspecting Loki's claims and querying counter-evidence on bottlenecks...")
    print("  * Loki inspecting Thor's claims and querying counter-evidence on buffer capacity...")

    thor_r2_task = asyncio.create_task(thor.act(case))
    loki_r2_task = asyncio.create_task(loki.act(case))

    await asyncio.gather(thor_r2_task, loki_r2_task)

    thor_attacks = [a for a in current_run.attacks if a.from_agent == "thor"]
    loki_attacks = [a for a in current_run.attacks if a.from_agent == "loki"]
    thor_defences = [d for d in current_run.defences if d.defence_id.startswith("DEF-THOR")]
    loki_defences = [d for d in current_run.defences if d.defence_id.startswith("DEF-LOKI")]

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

    # ---------------------------------------------------------------------------
    # Persist Runs to Blackboard (Supabase case_files)
    # ---------------------------------------------------------------------------
    try:
        runs_payload = [r.model_dump(mode="json") for r in case.runs]
        post_to_case_file(
            case_id=case.case_id,
            section="runs",
            payload=runs_payload,
        )
    except Exception as e:
        print(f"[Warning] Failed to persist runs to Supabase: {e}")

    print_banner("DEBATE COMPLETE: BLACKBOARD SYNCHRONIZED FOR ODIN JUDICIAL REVIEW")
    print(f"Total Claims on Blackboard : {len(current_run.claims)} (Thor: {len(thor_claims)}, Loki: {len(loki_claims)})")
    print(f"Total Attacks on Blackboard: {len(current_run.attacks)} (Thor: {len(thor_attacks)}, Loki: {len(loki_attacks)})")
    print(f"Total Defences Recorded    : {len(current_run.defences)}")
    print("All evidence citations grounded in Supabase runemark_documents and pre-cutoff clock.")

    return case


async def run_trial_pipeline(
    question: str,
    as_of: str = "2027-01-25",
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full integrated pipeline:
      1. Initialise case in Supabase.
      2. Run Heimdall Gatekeeper.
      3. Evaluate verdict:
         - If NOT 'real': Output case rejected / not found. Do NOT wake Thor & Loki.
         - If 'real': Wake Thor & Loki concurrently for debate.
    """
    print_banner("TRIAL OF THE NINE REALMS -- INTEGRATED INVESTIGATION & DEBATE")
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
        # Event is NOT confirmed real (rumour, unverifiable, or rejected)
        print_banner("CASE EVALUATION: REJECTED / DISRUPTION NOT FOUND")
        print(f"Verdict: {verdict_str.upper()} (Confidence: {confidence * 100:.0f}%)")
        print("Outcome: The disruption event was NOT found or verified as real in the corpus.")
        print("-> Thor and Loki agents will NOT be awakened.")
        print(f"-> Case {case_id} closed without debate.")

        # Update case status in database to rejected
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

    # Step 4: Approved Case -- Wake Thor & Loki for Debate
    print_banner("CASE EVALUATION: APPROVED (REAL) -- AWAKENING AGENTS")
    print(f"Verdict: REAL (Confidence: {confidence * 100:.0f}%)")
    print("Outcome: Disruption event confirmed real by official notice / evidence.")
    print("-> Awakening Thor (High Exposure) and Loki (Limited Exposure) concurrently...")

    as_of_date = date.fromisoformat(as_of)
    case_scope = heimdall_output.scope

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
    )

    completed_case = await run_thor_and_loki_debate(case)

    return {
        "case_id": case_id,
        "status": "completed",
        "verdict": verdict_str,
        "confidence": confidence,
        "reasons": reasons,
        "wake_next": wake_next,
        "case_file": completed_case,
    }
