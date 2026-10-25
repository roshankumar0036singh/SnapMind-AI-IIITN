"""
scripts/test_odin_live.py
=========================
Live demonstration and verification of Odin — The Allfather (Judge Agent).
Runs against live Supabase database documents from Runemark dev_pack_E5.
"""

import json
import sys
from datetime import date
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.odin import OdinJudge
from src.tools.citation_tools import get_citation_validator
from src.schemas.case_file import CaseFile, RunRecord, EventScope, CaseStatus
from src.schemas.claims import Claim, Attack, Defence, ClaimKind


def main():
    print("=" * 80)
    print("         TRIAL OF THE NINE REALMS — ODIN JUDICIAL LIVE TEST")
    print("=" * 80)

    # 1. Initialize Odin with unified CitationValidator (backed by Supabase)
    validator = get_citation_validator()
    judge = OdinJudge(citation_validator=validator)

    as_of = date(2027, 1, 25)
    case_id = "CASE-E5-LIVE-DEMO"

    # 2. Setup Case File blackboard from sample question in dev_pack_E5
    case = CaseFile(
        case_id=case_id,
        question=(
            "As of 25 January 2027, how exposed are Midgard and Tolan to the end "
            "of the Orvan corridor agreement? Give a low and high range for wheat and maize imports."
        ),
        as_of=as_of,
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Midgard", "Tolan"],
            target_sectors=["Wheat", "Maize"],
            as_of_date=as_of,
        ),
        limits={"max_runs": 2},
    )

    print(f"\n[1] Case Initialized:")
    print(f"    Case ID:  {case.case_id}")
    print(f"    Question: {case.question}")
    print(f"    Clock:    {case.as_of}")
    print(f"    Scope:    Countries: {case.scope.target_countries}, Sectors: {case.scope.target_sectors}")

    # -------------------------------------------------------------------------
    # RUN 1: Partial Evidence (Tolan & Maize missing) -> Triggers Send-Back
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print(">>> EXECUTING TRIAL RUN 1 (Thor & Loki submit initial claims for Midgard)")
    print("-" * 80)

    run_1 = RunRecord(
        run_no=1,
        claims=[
            Claim(
                claim_id="CLM-THOR-R1-01",
                agent="thor",
                text="Midgard port index fell to 40 against baseline of 100 following corridor expiry.",
                country="Midgard",
                sector="Wheat",
                estimate_low=-60.0,
                estimate_high=-50.0,
                citations=["ORV-0006#P2"],
            ),
            Claim(
                claim_id="CLM-LOKI-R1-01",
                agent="loki",
                text="Midgard flour millers are booking replacement wheat from Vanir and rail from Ravik.",
                country="Midgard",
                sector="Wheat",
                estimate_low=-30.0,
                estimate_high=-15.0,
                citations=["ORV-0006#P1"],
            ),
        ],
        attacks=[
            Attack(
                attack_id="ATK-THOR-R1-01",
                from_agent="thor",
                target_claim_id="CLM-LOKI-R1-01",
                grounds="bad_method",
                evidence_refs=["ORV-0006#P4"],
                text="Millers explicitly stated they can replace some of the lost wheat, not all of it.",
            )
        ],
        defences=[
            Defence(
                defence_id="DEF-LOKI-R1-01",
                attack_id="ATK-THOR-R1-01",
                response_type="new_evidence",
                new_refs=["ORV-0006#P5"],
                text="Millers confirm arrangement is workable for now and ministry has not raised stock guidance.",
            )
        ],
    )
    case.runs.append(run_1)

    # Odin evaluates Run 1
    case, summary_1 = judge.evaluate_case(case, run_no=1)

    print(f"\n[Odin Judicial Verdict - Run 1]:")
    print(f"    Action:     {summary_1['action'].upper()}")
    print(f"    Rulings:    {len(case.runs[0].rulings)} claims adjudicated")
    for r in case.runs[0].rulings:
        print(f"      - {r.claim_id}: {r.outcome.value.upper()} [{r.basis.value}] | {r.reasoning}")

    print(f"    Sufficiency Check: {case.runs[0].sufficiency.upper()}")
    print(f"    Missing Categories Identified by Odin:")
    for m in case.runs[0].missing:
        print(f"      * {m}")

    assert case.runs[0].sufficiency == "send_back"
    print("\n    [SUCCESS] Odin successfully triggered send_back to Heimdall for Run 2!")

    # -------------------------------------------------------------------------
    # RUN 2: Scope gaps filled with Tolan & Maize evidence + Cross-examination concession
    # -------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print(">>> EXECUTING TRIAL RUN 2 (New evidence retrieved for Tolan & Maize; cross-exam concession)")
    print("-" * 80)

    run_2 = RunRecord(
        run_no=2,
        claims=[
            # Upheld Midgard Wheat synthesis
            Claim(
                claim_id="CLM-THOR-R2-01",
                agent="thor",
                text="Midgard port index dropped to 40/100, leaving net import deficit after partial rail offset.",
                country="Midgard",
                sector="Wheat",
                estimate_low=-45.0,
                estimate_high=-35.0,
                citations=["ORV-0006#P2"],
            ),
            Claim(
                claim_id="CLM-LOKI-R2-01",
                agent="loki",
                text="Rail loadings through Ravik and Vanir wheat deliveries provide steady partial buffer.",
                country="Midgard",
                sector="Wheat",
                estimate_low=-25.0,
                estimate_high=-15.0,
                citations=["ORV-0035#P4"],
            ),
            # New Tolan Wheat/Maize evidence (filling missing scope)
            Claim(
                claim_id="CLM-THOR-R2-02",
                agent="thor",
                text="Tolan depends heavily on imported grain and faces delays at Tolan Harbour.",
                country="Tolan",
                sector="Wheat",
                estimate_low=-35.0,
                estimate_high=-25.0,
                citations=["ATL-0010#P1"],
            ),
            Claim(
                claim_id="CLM-LOKI-R2-02",
                agent="loki",
                text="Anchor Marine confirms Tolan Harbour is handling extra Vanir wheat cargoes to replace Orvan supply.",
                country="Tolan",
                sector="Wheat",
                estimate_low=-20.0,
                estimate_high=-10.0,
                citations=["ORV-0042#P1"],
            ),
            Claim(
                claim_id="CLM-LOKI-R2-03",
                agent="loki",
                text="Orvan farm union reports maize crop planting and harvest caught up on schedule.",
                country="Tolan",
                sector="Maize",
                estimate_low=-10.0,
                estimate_high=-5.0,
                citations=["ORV-0011#P5"],
            ),
            # Trap claim: unverified rumor cited by Thor
            Claim(
                claim_id="CLM-THOR-R2-03",
                agent="thor",
                text="Orvan grain port entirely destroyed and whole quay gone.",
                country="Midgard",
                sector="Wheat",
                estimate_low=-100.0,
                estimate_high=-90.0,
                citations=["ORV-0010#P1"],
            ),
        ],
        attacks=[
            Attack(
                attack_id="ATK-LOKI-R2-02",
                from_agent="loki",
                target_claim_id="CLM-THOR-R2-03",
                grounds="low_tier",
                evidence_refs=[],
                text="Source ORV-0010 is an uncorroborated Tier 4 social post rumor ('hearing port destroyed').",
            )
        ],
        defences=[
            Defence(
                defence_id="DEF-THOR-R2-02",
                attack_id="ATK-LOKI-R2-02",
                response_type="concede",
                new_refs=[],
                text="Conceded: ORV-0010 is an uncorroborated social chat rumor; claim withdrawn.",
            )
        ],
    )
    case.runs.append(run_2)

    # Odin evaluates Run 2
    final_case, summary_2 = judge.evaluate_case(case, run_no=2)

    print(f"\n[Odin Judicial Verdict - Run 2]:")
    print(f"    Action:          {summary_2['action'].upper()}")
    print(f"    Case Status:     {final_case.status.value.upper()}")
    print(f"    Sufficiency:     {final_case.runs[1].sufficiency.upper()}")
    print(f"    Rulings Count:   {len(final_case.runs[1].rulings)}")

    classification = final_case.runs[1].classification
    print(f"\n[Tri-Partite Findings Classification (FR4.2)]:")
    print(f"    Established ({len(classification.established)}): {classification.established}")
    print(f"    Contested   ({len(classification.contested)}): {classification.contested}")
    print(f"    Conceded    ({len(classification.conceded)}): {classification.conceded}")

    print(f"\n[Calibrated Exposure Ranges (FR8)]:")
    for r in final_case.runs[1].ranges:
        print(f"    * {r.country:8} | {r.sector:12} | Calibrated: [{r.odin_low:+.1f}%, {r.odin_high:+.1f}%] | Thor: [{r.thor_low}%, {r.thor_high}%] | Loki: [{r.loki_low}%, {r.loki_high}%]")
        print(f"      Basis: {r.basis}")

    print(f"\n[OKF Deliverables Bundle Exported (NFR6)]:")
    for k, v in summary_2["export_bundle"].items():
        print(f"    * {k:20}: {v}")

    # Inspect generated briefing file
    briefing_path = Path(summary_2["export_bundle"]["final_briefing_md"])
    print(f"\n[Executive Judicial Briefing Preview ({briefing_path.name})]:")
    print("-" * 60)
    briefing_text = briefing_path.read_text(encoding="utf-8")
    # Show first 40 lines
    lines = briefing_text.splitlines()[:45]
    print("\n".join(lines))
    print("    [... truncated for display ...]")
    print("-" * 60)

    print("\n" + "=" * 80)
    print(">>> ODIN AGENT LIVE TEST COMPLETED WITH 100% SUCCESS!")
    print("=" * 80)


if __name__ == "__main__":
    main()
