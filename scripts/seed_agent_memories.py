"""
scripts/seed_agent_memories.py
==============================
Seeds initial strategic domain lessons into Supabase `agent_memories` table
for Thor, Loki, Heimdall, and Odin.
Enforces FR6.1 and provides the baseline lessons needed for Acceptance Check 9
(behavior modification on first case execution).
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List

from src.supabase_client import get_supabase_admin


SEED_MEMORIES: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # Thor (The Alarm - High Exposure)
    # -------------------------------------------------------------------------
    {
        "id": "MEM-THOR-SEED-01",
        "agent_id": "thor",
        "memory_type": "source_lesson",
        "content": "Tier 4 social feeds in maritime chokepoints frequently spread unverified rumors. Avoid Tier 4 sources and restrict search ceiling to Tier 3 when investigating port disruptions.",
        "scope": "global",
        "basis_refs": ["DOC-HIST-001"],
        "confidence": 0.95,
        "created_run": 1,
        "status": "active",
    },
    {
        "id": "MEM-THOR-SEED-02",
        "agent_id": "thor",
        "memory_type": "attack_tactic",
        "content": "Loki frequently asserts commercial substitution without checking transit lag. Attack mitigation claims by demanding proof of lead-time feasibility and rolling stock deficits.",
        "scope": "claim_type",
        "basis_refs": ["DOC-HIST-002"],
        "confidence": 0.90,
        "created_run": 1,
        "status": "active",
    },
    {
        "id": "MEM-THOR-SEED-03",
        "agent_id": "thor",
        "memory_type": "calculation_method",
        "content": "When calculating maritime export deficits, compare current disrupted month against 12-month rolling average to substantiate acute physical exposure.",
        "scope": "sector",
        "basis_refs": ["TRD-HIST-001"],
        "confidence": 0.92,
        "created_run": 1,
        "status": "active",
    },

    # -------------------------------------------------------------------------
    # Loki (The Trickster - Limited Exposure)
    # -------------------------------------------------------------------------
    {
        "id": "MEM-LOKI-SEED-01",
        "agent_id": "loki",
        "memory_type": "search_strategy",
        "content": "In agricultural disruptions, domestic buffer stocks and rail diversions offset immediate import halts. Always search for strategic reserves and alternative rail transit.",
        "scope": "sector",
        "basis_refs": ["DOC-HIST-003"],
        "confidence": 0.95,
        "created_run": 1,
        "status": "active",
    },
    {
        "id": "MEM-LOKI-SEED-02",
        "agent_id": "loki",
        "memory_type": "source_lesson",
        "content": "Tabloid and regional commentary outlets (Tier 4) exaggerate initial disruption shocks by up to 300%. Reject Tier 4 outlets from quantitative trade impact estimations.",
        "scope": "global",
        "basis_refs": ["DOC-HIST-004"],
        "confidence": 0.90,
        "created_run": 1,
        "status": "active",
    },
    {
        "id": "MEM-LOKI-SEED-03",
        "agent_id": "loki",
        "memory_type": "attack_tactic",
        "content": "Thor cherry-picks single-month trade dips. Defeat high-exposure claims by computing 12-month trailing moving averages in trade tables and checking inventory buffers.",
        "scope": "claim_type",
        "basis_refs": ["TRD-HIST-002"],
        "confidence": 0.93,
        "created_run": 1,
        "status": "active",
    },

    # -------------------------------------------------------------------------
    # Heimdall (Gatekeeper)
    # -------------------------------------------------------------------------
    {
        "id": "MEM-HEIM-SEED-01",
        "agent_id": "heimdall",
        "memory_type": "verification_rule",
        "content": "Events reported solely by Tier 4 social outlets without Tier 1 or Tier 2 official confirmation must be classified as rumour or unverified.",
        "scope": "global",
        "basis_refs": ["DOC-HIST-005"],
        "confidence": 0.98,
        "created_run": 1,
        "status": "active",
    },

    # -------------------------------------------------------------------------
    # Odin (The Allfather Judge)
    # -------------------------------------------------------------------------
    {
        "id": "MEM-ODIN-SEED-01",
        "agent_id": "odin",
        "memory_type": "ruling_precedent",
        "content": "Claims citing sources dated after the as-of Simulated Clock must be strictly rejected under the temporal gate, regardless of source credibility tier.",
        "scope": "global",
        "basis_refs": ["RULE-SIMULATED-CLOCK"],
        "confidence": 1.0,
        "created_run": 1,
        "status": "active",
    },
]


def seed_memories() -> int:
    """Inserts seed memory records into Supabase agent_memories table."""
    print("=" * 70)
    print("  SEEDING AGENT MEMORIES INTO SUPABASE")
    print("=" * 70)

    try:
        db = get_supabase_admin()
    except Exception as e:
        print(f"[Error] Failed to connect to Supabase: {e}", file=sys.stderr)
        return 1

    success_count = 0
    for mem in SEED_MEMORIES:
        try:
            db.table("agent_memories").upsert(mem, on_conflict="id").execute()
            print(f"  [OK] Seeded {mem['id']} for {mem['agent_id'].upper()}: {mem['memory_type']}")
            success_count += 1
        except Exception as e:
            print(f"  [Error] Failed to seed {mem['id']}: {e}", file=sys.stderr)

    print(f"\nSuccessfully seeded {success_count}/{len(SEED_MEMORIES)} agent memory records.")
    return 0


if __name__ == "__main__":
    sys.exit(seed_memories())
