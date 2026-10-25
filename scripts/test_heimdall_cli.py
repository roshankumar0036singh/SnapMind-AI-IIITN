"""
scripts/test_heimdall_cli.py
============================
Interactive CLI to test the Heimdall Gatekeeper agent.

Usage:
    python scripts/test_heimdall_cli.py
    python scripts/test_heimdall_cli.py --question "..." --as-of 2027-01-25
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.heimdall.agent import initialise_case, run_heimdall


def main():
    parser = argparse.ArgumentParser(description="Test Heimdall Gatekeeper Agent")
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
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  HEIMDALL GATEKEEPER — CASE INVESTIGATION TEST")
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
    print("\n" + "=" * 60)
    print("  HEIMDALL VERDICT & CASE FILE")
    print("=" * 60)
    print(f"Verdict        : {output.verification.verdict.upper()}")
    print(f"Confidence     : {output.verification.confidence:.2f}")
    print(f"Reasons        : {output.verification.reasons or 'None'}")
    print(f"Evidence Count : {len(output.evidence_index)}")
    print(f"Wake Next      : {output.wake_next}")
    print("-" * 60)

    print("\nStructured JSON Output Preview:")
    print(json.dumps(output.model_dump(), indent=2, default=str)[:1000] + "\n...")


if __name__ == "__main__":
    main()
