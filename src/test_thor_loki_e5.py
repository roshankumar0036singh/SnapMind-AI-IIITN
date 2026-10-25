"""
src/test_thor_loki_e5.py
========================
Test harness for Thor and Loki agents on the real dev_pack_E5 dataset.

Assumptions:
  - Heimdall has approved the case as 'real' (Event E5: Orvan Corridor Collapse).
  - Question: "As of 25 January 2027, how exposed are Midgard and Tolan to the end of the Orvan corridor agreement? Give a low and high range for wheat and maize imports."
  - Simulated Clock as-of date: 2027-01-25.

Execution:
  - Round 1: Concurrent hybrid embedding & keyword search across Supabase runemark_documents.
    Thor argues HIGH exposure; Loki argues LIMITED exposure.
  - Round 2: Concurrent cross-examination (attacks, counter-evidence, and concessions).
"""

import asyncio
import os
import sys
from datetime import date

# Ensure clean UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.schemas.case_file import CaseFile, EventScope, VerificationVerdict, CaseStatus, RunRecord
from src.agents.thor.thor_agent import ThorAgent
from src.agents.loki.loki_agent import LokiAgent


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    print("\n" + "-" * 80)
    print(f">>> {title}")
    print("-" * 80)


async def run_e5_trial():
    # ---------------------------------------------------------------------------
    # Step 1: Initialize Case with Heimdall's Approval
    # ---------------------------------------------------------------------------
    print_banner("TRIAL OF THE NINE REALMS -- THOR & LOKI DEBATE (DEV PACK E5)")

    sample_q_path = os.path.join("data", "test_packs", "dev_pack_E5", "sample_question.txt")
    if os.path.exists(sample_q_path):
        with open(sample_q_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("QUESTION")]
            question = lines[0] if lines else "As of 25 January 2027, how exposed are Midgard and Tolan to the end of the Orvan corridor agreement? Give a low and high range for wheat and maize imports."
    else:
        question = "As of 25 January 2027, how exposed are Midgard and Tolan to the end of the Orvan corridor agreement? Give a low and high range for wheat and maize imports."

    as_of = date(2027, 1, 25)

    print(f"[QUESTION]: \"{question}\"")
    print(f"[AS-OF DATE]: {as_of} (Strict clock cutoff enforced)")
    print(f"[TARGETS]: Countries: Midgard, Tolan | Sectors: Wheat, Maize | Event: E5")

    # Simulate Heimdall's verified Case File
    case = CaseFile(
        case_id="CASE_E5_ORVAN_CORRIDOR",
        question=question,
        as_of=as_of,
        status=CaseStatus.OPEN,
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Midgard", "Tolan"],
            target_sectors=["wheat", "maize"],
            as_of_date=as_of,
        ),
        verification=VerificationVerdict(
            verdict="real",
            confidence=1.0,
            reasons=[
                "Confirmed real by Tier 1 Regional Port Authority Notice (ORV-0005) and multiple trade reports.",
                "Corridor agreement has lapsed; maritime grain shipments halted."
            ],
            supporting_docs=["ORV-0005", "ORV-0024"],
            message_to_user="Disruption event confirmed real and active. Trial proceeding to debate.",
        ),
        runs=[RunRecord(run_no=1)],
    )

    print_section("PHASE 1: HEIMDALL VERIFICATION STATUS")
    print(f"Status: [{case.verification.verdict.upper()}] (Confidence: {case.verification.confidence * 100:.0f}%)")
    for r in case.verification.reasons:
        print(f"  * {r}")
    print(f"Heimdall signal: Case approved for Thor and Loki simultaneous wake-up.")

    # Instantiate Agents
    thor = ThorAgent()
    loki = LokiAgent()

    # ---------------------------------------------------------------------------
    # Step 2: Round 1 -- Concurrent Autonomous Search & Claim Synthesis
    # ---------------------------------------------------------------------------
    print_section("PHASE 2: ROUND 1 -- PARALLEL EMBEDDING SEARCH & CLAIM SYNTHESIS")
    print("Executing Thor and Loki concurrently via asyncio.gather()...")
    print("  * Thor querying Supabase for: closures, blockades, capacity drops, maritime deficits...")
    print("  * Loki querying Supabase for: alternative rail corridors, inventory stockpiles, commercial substitution...")

    thor_r1_task = asyncio.create_task(thor.act(case))
    loki_r1_task = asyncio.create_task(loki.act(case))

    thor_r1, loki_r1 = await asyncio.gather(thor_r1_task, loki_r1_task)

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
    # Step 3: Round 2 -- Concurrent Cross-Examination (Attacks & Defences)
    # ---------------------------------------------------------------------------
    print_section("PHASE 3: ROUND 2 -- CROSS-EXAMINATION & EVIDENCE-BASED ATTACKS")
    print("Executing Round 2 concurrently via asyncio.gather()...")
    print("  * Thor inspecting Loki's claims and querying counter-evidence on rail bottlenecks...")
    print("  * Loki inspecting Thor's claims and querying counter-evidence on stockpile buffers...")

    thor_r2_task = asyncio.create_task(thor.act(case))
    loki_r2_task = asyncio.create_task(loki.act(case))

    thor_r2, loki_r2 = await asyncio.gather(thor_r2_task, loki_r2_task)

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

    print_section("PHASE 4: DEFENCES & CONCESSIONS")
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

    print_banner("TRIAL STAGE COMPLETE: READY FOR ODIN JUDICIAL EVALUATION")
    print(f"Total Claims on Blackboard : {len(current_run.claims)} (Thor: {len(thor_claims)}, Loki: {len(loki_claims)})")
    print(f"Total Attacks on Blackboard: {len(current_run.attacks)} (Thor: {len(thor_attacks)}, Loki: {len(loki_attacks)})")
    print(f"Total Defences Recorded    : {len(current_run.defences)}")
    print("All citations strictly grounded in Supabase runemark_documents and pre-cutoff clock (2027-01-25).")


if __name__ == "__main__":
    asyncio.run(run_e5_trial())
