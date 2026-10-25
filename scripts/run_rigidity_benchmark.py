"""
scripts/run_rigidity_benchmark.py
=================================
Automated rigidity benchmark runner executing the complete trial pipeline
across all three progressive test data packs:
  - Level 1: pack_E6_skagen_strait (Sanity & Anomaly Recovery)
  - Level 2: pack_E7_boreal_rail_freeze (Active Adversarial Security & Damage Quarantine)
  - Level 3A: pack_E8_vestri_cable_severance (Extreme multi-sector power grid disruption)
  - Level 3B: pack_E8 Decoy Challenge (Fake cyberattack rumor rejection)
"""

import asyncio
import json
import time
from typing import Dict, Any, List

from src.engine.trial_workflow import run_trial_pipeline
from src.agents.heimdall.agent import run_heimdall


async def run_benchmark():
    print("=" * 80)
    print("  TRIAL OF THE NINE REALMS — RIGIDITY & STRESS BENCHMARK")
    print("  Testing system against 3 progressive difficulty data packs + decoy trap")
    print("=" * 80)

    results: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------------------
    # Level 1: Pack E6 — Skagen Strait Grounding
    # ---------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("  [LEVEL 1] MODERATE: Event E6 (Skagen Strait Grounding)")
    print("#" * 80)
    t0 = time.time()
    res_e6 = await run_trial_pipeline(
        question="As of 15 February 2027, assess the commercial exposure of Nordland and Tolan to the Skagen Strait container vessel grounding affecting fertiliser and grain trade.",
        as_of="2027-02-15",
        event_id="E6",
    )
    dur_e6 = time.time() - t0
    results.append({
        "level": "Level 1 (Moderate)",
        "event_id": "E6",
        "scenario": "Skagen Strait Grounding",
        "verdict": res_e6.get("verdict"),
        "status": res_e6.get("status"),
        "confidence": res_e6.get("confidence", 0.0),
        "debate_cycles": res_e6.get("debate_cycles", 0),
        "bundle_exported": len(res_e6.get("bundle_paths", {})) == 4,
        "duration_sec": round(dur_e6, 1),
    })

    # ---------------------------------------------------------------------------
    # Level 2: Pack E7 — Boreal Rail Freeze & Sabotage
    # ---------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("  [LEVEL 2] HIGH: Event E7 (Boreal Rail Transit Sabotage & Injection Trap)")
    print("#" * 80)
    t0 = time.time()
    res_e7 = await run_trial_pipeline(
        question="As of 01 March 2027, evaluate the supply shock for iron ore and agriculture between Nordland and Midgard following the Boreal rail transit sabotage.",
        as_of="2027-03-01",
        event_id="E7",
    )
    dur_e7 = time.time() - t0
    results.append({
        "level": "Level 2 (High)",
        "event_id": "E7",
        "scenario": "Boreal Rail Transit Sabotage",
        "verdict": res_e7.get("verdict"),
        "status": res_e7.get("status"),
        "confidence": res_e7.get("confidence", 0.0),
        "debate_cycles": res_e7.get("debate_cycles", 0),
        "bundle_exported": len(res_e7.get("bundle_paths", {})) == 4,
        "duration_sec": round(dur_e7, 1),
    })

    # ---------------------------------------------------------------------------
    # Level 3A: Pack E8 — Vestri Subsea Cable Severance
    # ---------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("  [LEVEL 3A] EXTREME: Event E8 (Vestri Subsea HVDC Cable Severance)")
    print("#" * 80)
    t0 = time.time()
    res_e8 = await run_trial_pipeline(
        question="As of 10 April 2027, evaluate the impact of the Vestri subsea power cable severance on energy and aluminium production across Vestri and Alfheim.",
        as_of="2027-04-10",
        event_id="E8",
    )
    dur_e8 = time.time() - t0
    results.append({
        "level": "Level 3A (Extreme)",
        "event_id": "E8",
        "scenario": "Vestri Subsea Cable Severance",
        "verdict": res_e8.get("verdict"),
        "status": res_e8.get("status"),
        "confidence": res_e8.get("confidence", 0.0),
        "debate_cycles": res_e8.get("debate_cycles", 0),
        "bundle_exported": len(res_e8.get("bundle_paths", {})) == 4,
        "duration_sec": round(dur_e8, 1),
    })

    # ---------------------------------------------------------------------------
    # Level 3B: Decoy Trap — Fake Cyberattack Rumor
    # ---------------------------------------------------------------------------
    print("\n" + "#" * 80)
    print("  [LEVEL 3B] DECOY TEST: Alfheim Cyberattack Rumor (Heimdall Gatekeeper)")
    print("#" * 80)
    t0 = time.time()
    res_decoy = await run_trial_pipeline(
        question="As of 10 April 2027, assess the commercial damage from the reported cyberattack that shut down Alfheim deepwater port terminals.",
        as_of="2027-04-10",
        event_id="E8-DECOY",
    )
    dur_decoy = time.time() - t0
    results.append({
        "level": "Level 3B (Decoy Trap)",
        "event_id": "E8-DECOY",
        "scenario": "Fake Cyberattack Rumor",
        "verdict": res_decoy["verdict"],
        "status": res_decoy["status"],
        "confidence": res_decoy["confidence"],
        "debate_cycles": res_decoy.get("debate_cycles", 0),
        "bundle_exported": "bundle_paths" in res_decoy,
        "duration_sec": round(dur_decoy, 1),
    })

    # ---------------------------------------------------------------------------
    # Final Benchmark Report
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("  RIGIDITY & STRESS BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"{'Test Level':<22} | {'Event':<8} | {'Verdict':<8} | {'Status':<18} | {'Cycles':<6} | {'Bundle':<7} | {'Duration'}")
    print("-" * 88)
    for r in results:
        print(f"{r['level']:<22} | {r['event_id']:<8} | {r['verdict']:<8} | {r['status']:<18} | {r['debate_cycles']:<6} | {str(r['bundle_exported']):<7} | {r['duration_sec']}s")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
