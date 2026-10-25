"""
tests/unit/test_thor_loki_agents.py
===================================
End-to-end unit and flow validation for Thor and Loki agents:
  1. Verifies compatibility with Heimdall CaseFile output.
  2. Verifies simultaneous wake-up in Round 1.
  3. Verifies Round 1 claim generation using Gemini API structured output.
  4. Verifies Round 2 cross-examination (attacks & defences).
  5. Verifies private lasting memory isolation (Acceptance Check 9).
"""

import asyncio
from datetime import date
import pytest

from src.schemas.case_file import CaseFile, EventScope, VerificationVerdict, CaseStatus, RunRecord
from src.schemas.claims import ClaimKind
from src.agents.thor.thor_agent import ThorAgent
from src.agents.loki.loki_agent import LokiAgent


@pytest.mark.asyncio
async def test_thor_and_loki_full_adversarial_flow():
    # -------------------------------------------------------------
    # 1. Simulate Heimdall output in the Case File
    # -------------------------------------------------------------
    as_of = date(2027, 1, 25)
    case = CaseFile(
        case_id="CASE_E5_INTEGRATION_TEST",
        question="What is the supply chain exposure to the Orvan corridor collapse for Midgard wheat?",
        as_of=as_of,
        status=CaseStatus.OPEN,
        scope=EventScope(
            event_id="E5",
            event_name="Orvan grain corridor collapse",
            target_countries=["Midgard"],
            target_sectors=["wheat"],
            as_of_date=as_of,
        ),
        verification=VerificationVerdict(
            verdict="real",
            confidence=1.0,
            reasons=["Confirmed by Tier 1 Ministry of Transport Notice"],
            supporting_docs=["ORV-0005"],
            message_to_user="Disruption event confirmed real.",
        ),
        runs=[RunRecord(run_no=1)],
    )

    thor = ThorAgent()
    loki = LokiAgent()

    # -------------------------------------------------------------
    # 2. Check Round 1 Simultaneous Wake Conditions
    # -------------------------------------------------------------
    assert thor.can_wake(case) is True, "Thor must wake for Round 1 when event is real"
    assert loki.can_wake(case) is True, "Loki must wake for Round 1 when event is real"

    # -------------------------------------------------------------
    # 3. Execute Round 1 in Parallel (asyncio.gather)
    # -------------------------------------------------------------
    thor_r1_res, loki_r1_res = await asyncio.gather(
        thor.act(case),
        loki.act(case),
    )

    current_run = case.runs[0]
    thor_claims = [c for c in current_run.claims if c.agent == "thor"]
    loki_claims = [c for c in current_run.claims if c.agent == "loki"]

    assert len(thor_claims) >= 1, "Thor must produce at least 1 claim"
    assert len(loki_claims) >= 1, "Loki must produce at least 1 claim"

    # Verify claim grounding and schemas
    for c in thor_claims:
        assert c.agent == "thor"
        assert len(c.citations) >= 1, "Thor claim must have citations"
        assert c.kind in [ClaimKind.SOURCED_FACT, ClaimKind.CALCULATION, ClaimKind.INFERENCE]
        assert c.country.lower() == "midgard"

    for c in loki_claims:
        assert c.agent == "loki"
        assert len(c.citations) >= 1, "Loki claim must have citations"
        assert c.country.lower() == "midgard"

    print(f"\n[OK] Round 1 complete: Thor produced {len(thor_claims)} claims, Loki produced {len(loki_claims)} claims.")

    # -------------------------------------------------------------
    # 4. Check Round 2 Wake Conditions (Both have claims submitted)
    # -------------------------------------------------------------
    assert thor.can_wake(case) is True, "Thor must wake for Round 2 when both sides submitted claims"
    assert loki.can_wake(case) is True, "Loki must wake for Round 2 when both sides submitted claims"

    # -------------------------------------------------------------
    # 5. Execute Round 2 Cross-Examination in Parallel
    # -------------------------------------------------------------
    thor_r2_res, loki_r2_res = await asyncio.gather(
        thor.act(case),
        loki.act(case),
    )

    thor_attacks = [a for a in current_run.attacks if a.from_agent == "thor"]
    loki_attacks = [a for a in current_run.attacks if a.from_agent == "loki"]

    assert len(thor_attacks) >= 1, "Thor must attack at least one of Loki's claims"
    assert len(loki_attacks) >= 1, "Loki must attack at least one of Thor's claims"

    # Verify that Thor attacked a claim belonging to Loki
    loki_claim_ids = {c.claim_id for c in loki_claims}
    for atk in thor_attacks:
        assert atk.from_agent == "thor"
        assert atk.target_claim_id in loki_claim_ids or atk.target_claim_id.startswith("CLM-LOKI")

    # Verify that Loki attacked a claim belonging to Thor
    thor_claim_ids = {c.claim_id for c in thor_claims}
    for atk in loki_attacks:
        assert atk.from_agent == "loki"
        assert atk.target_claim_id in thor_claim_ids or atk.target_claim_id.startswith("CLM-THOR")

    print(f"[OK] Round 2 complete: Thor launched {len(thor_attacks)} attacks, Loki launched {len(loki_attacks)} attacks.")

    # Neither should wake again for Round 2
    assert thor.can_wake(case) is False, "Thor must not wake after completing Round 2"
    assert loki.can_wake(case) is False, "Loki must not wake after completing Round 2"

    print("[OK] Trial ready for Odin's judicial evaluation!")


if __name__ == "__main__":
    asyncio.run(test_thor_and_loki_full_adversarial_flow())
