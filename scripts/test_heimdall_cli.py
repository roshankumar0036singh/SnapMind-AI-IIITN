"""
scripts/test_heimdall_cli.py
============================
Interactive CLI to test the Heimdall Gatekeeper agent integrated with
the Thor and Loki adversarial debate workflow.

Usage:
    # 1. Negative test (Unverifiable question -> Rejected, Thor & Loki NOT called):
    python scripts/test_heimdall_cli.py

    # 2. Positive test on real E5 dataset (Corridor collapse -> REAL -> Thor & Loki debate):
    python scripts/test_heimdall_cli.py --e5

    # 3. Custom question:
    python scripts/test_heimdall_cli.py --question "..." --as-of 2027-01-25 --event-id E5
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

# Ensure clean UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.heimdall.agent import initialise_case, run_heimdall


def main():
    parser = argparse.ArgumentParser(description="Test Heimdall Gatekeeper and Debate Workflow")
    parser.add_argument(
        "--question",
        type=str,
        default="Did the port closure at Skagen disrupt titanium exports before 2027-01-25?",
        help="Investigation question for Heimdall",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default="2027-01-25",
        help="Simulated clock cut-off date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--event-id",
        type=str,
        default=None,
        help="Optional known event ID (e.g., E5)",
    )
    parser.add_argument(
        "--e5",
        action="store_true",
        help="Automatically load dev_pack_E5 question and parameters (Orvan corridor collapse)",
    )
    parser.add_argument(
        "--no-debate",
        action="store_true",
        help="Only run Heimdall gatekeeper without triggering Thor and Loki debate",
    )
    args = parser.parse_args()

    # If --e5 is specified, load question from sample_question.txt
    if args.e5:
        sample_q_path = os.path.join("data", "test_packs", "dev_pack_E5", "sample_question.txt")
        if os.path.exists(sample_q_path):
            with open(sample_q_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("QUESTION")]
                if lines:
                    args.question = lines[0]
        args.as_of = "2027-01-25"
        args.event_id = "E5"

    print("\n" + "=" * 60)
    print("  HEIMDALL GATEKEEPER -- CASE INVESTIGATION TEST")
    print("=" * 60)
    print(f"Question   : {args.question}")
    print(f"As-of Date : {args.as_of}")
    print(f"Event ID   : {args.event_id or 'Auto-detect'}")
    print("-" * 60)

    # 1. Initialize case in Supabase
    print("[1/2] Initializing Case File in Supabase...")
    case_id = initialise_case(
        question=args.question,
        as_of_date=args.as_of,
        event_id=args.event_id,
    )
    print(f"      Created Case ID: {case_id}")

    # 2. Run Heimdall Agent
    print("[2/2] Running Heimdall Gatekeeper...")
    output = run_heimdall(
        case_id=case_id,
        question=args.question,
        as_of_date=args.as_of,
        event_id=args.event_id,
    )

    # 3. Print Results
    verdict = output.verification.verdict.lower()
    confidence = output.verification.confidence
    wake_next = output.wake_next

    print("\n" + "=" * 60)
    print("  HEIMDALL VERDICT & CASE FILE")
    print("=" * 60)
    print(f"Verdict        : {verdict.upper()}")
    print(f"Confidence     : {confidence:.2f}")
    print(f"Reasons        : {output.verification.reasons or 'None'}")
    print(f"Evidence Count : {len(output.evidence_index)}")
    print(f"Wake Next      : {wake_next}")
    print("-" * 60)

    # 4. Integrate Thor and Loki conditional execution based on verdict
    if verdict != "real" or wake_next != "thor_and_loki":
        print("\n" + "=" * 60)
        print("  CASE STATUS: REJECTED / DISRUPTION NOT FOUND")
        print("=" * 60)
        print(f"Heimdall determined the case is [{verdict.upper()}].")
        if output.verification.reasons:
            print("Reasons:")
            for r in output.verification.reasons:
                print(f"  * {r}")
        print("\n[OUTCOME]: The disruption event was not found or verified in the corpus.")
        print("-> Thor and Loki agents are NOT awakened.")
        print(f"-> Case {case_id} closed without debate.\n")
    else:
        print("\n" + "=" * 60)
        print("  CASE STATUS: APPROVED (REAL) -- AWAKENING AGENTS")
        print("=" * 60)
        print(f"Heimdall verified disruption event as REAL (Confidence: {confidence * 100:.0f}%).")
        print("Supporting Evidence Documents:")
        for ref in getattr(output.verification, "supporting_refs", []):
            print(f"  * {ref}")
        print("\n[OUTCOME]: Case approved for trial! Waking Thor and Loki concurrently...")
        print("=" * 60)

        if not args.no_debate:
            from src.engine.trial_workflow import run_thor_and_loki_debate
            from src.schemas.case_file import (
                CaseFile,
                EventScope,
                VerificationVerdict,
                CaseStatus,
                RunRecord,
            )

            as_of_date = date.fromisoformat(args.as_of)
            case = CaseFile(
                case_id=case_id,
                question=args.question,
                as_of=as_of_date,
                status=CaseStatus.OPEN,
                scope=EventScope(
                    event_id=output.scope.event_id or args.event_id or "E5",
                    event_name=output.scope.event_name or output.event_name or "Disruption Event",
                    target_countries=output.scope.countries or ["Midgard", "Tolan"],
                    target_sectors=output.scope.sectors or ["wheat", "maize"],
                    as_of_date=as_of_date,
                ),
                verification=VerificationVerdict(
                    verdict=verdict,
                    confidence=confidence,
                    reasons=output.verification.reasons,
                    supporting_docs=getattr(output.verification, "supporting_refs", []),
                    message_to_user="Disruption event confirmed real. Case approved for debate.",
                ),
                runs=[RunRecord(run_no=1)],
            )

            asyncio.run(run_thor_and_loki_debate(case))


if __name__ == "__main__":
    main()
