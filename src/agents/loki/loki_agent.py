from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from src.agents.base import BaseAgent
from src.schemas.case_file import CaseFile, RunRecord
from src.schemas.claims import Claim, Attack, Defence
from src.agents.prompts.loki_prompts import (
    LOKI_SYSTEM_PROMPT,
    LOKI_CLAIM_GENERATION_PROMPT,
    LOKI_CROSS_EXAMINATION_PROMPT
)
from src.agents.loki.loki_tools import LokiToolsBinding

class LokiRound1Output(BaseModel):
    claims: List[Claim]

class LokiRound2Output(BaseModel):
    attacks: List[Attack]
    defences: List[Defence]

class LokiAgent(BaseAgent):
    """
    Loki: The Trickster.
    Advocate for Limited Supply-Chain Exposure & Resilience.
    Runs autonomously via deterministic wake conditions and calls Supabase tools.
    """
    def __init__(self):
        super().__init__("loki")
        self.tools = LokiToolsBinding()

    def _get_current_run(self, case: CaseFile) -> RunRecord:
        """Helper to get or initialize the active run record from the blackboard."""
        if not case.runs:
            run = RunRecord(run_no=1)
            case.runs.append(run)
            return run
        return case.runs[-1]

    def can_wake(self, case: CaseFile) -> bool:
        """
        Deterministic wake-up condition:
        1. Case verification is 'real' and Loki has 0 claims in current run (Round 1).
        2. Both Thor and Loki have claims, but Loki has 0 attacks in current run (Round 2).
        """
        if not case.verification or case.verification.verdict != "real":
            return False

        current_run = self._get_current_run(case)
        thor_claims = [c for c in current_run.claims if c.agent == "thor"]
        loki_claims = [c for c in current_run.claims if c.agent == "loki"]
        loki_attacks = [a for a in current_run.attacks if a.from_agent == "loki"]

        # Round 1 condition: Loki needs to submit claims
        if len(loki_claims) == 0:
            return True

        # Round 2 condition: Both submitted claims, but Loki hasn't attacked yet
        if len(thor_claims) > 0 and len(loki_claims) > 0 and len(loki_attacks) == 0:
            return True

        return False

    async def act(self, case: CaseFile) -> Dict[str, Any]:
        """Execute Loki's turn based on current trial state."""
        current_run = self._get_current_run(case)
        thor_claims = [c for c in current_run.claims if c.agent == "thor"]
        thor_attacks = [a for a in current_run.attacks if a.from_agent == "thor"]

        # 1. Read Loki's private lasting memory (Acceptance Check 9)
        lessons = self.memory.read_memories()
        max_tier_filter = 4
        memory_notes = []

        for lesson in lessons:
            content = lesson.get("content", "")
            memory_notes.append(content)
            if "avoid tier 4" in content.lower():
                max_tier_filter = 3
                self.memory.log_event("query_changed_by_memory", {
                    "reason": "Restricted max_tier to 3 due to prior lesson",
                    "previous_filter": 4,
                    "new_filter": 3
                })

        memory_context = "\n".join([f"- {note}" for note in memory_notes]) if memory_notes else "No prior lessons."

        # -------------------------------------------------------------
        # ROUND 1: GATHER RESILIENCE EVIDENCE FROM SUPABASE & SUBMIT CLAIMS
        # -------------------------------------------------------------
        loki_claims = [c for c in current_run.claims if c.agent == "loki"]
        if len(loki_claims) == 0:
            evidence = self.tools.gather_round1_evidence(case, max_tier=max_tier_filter)

            docs_text = "\n\n".join([
                f"[{d.get('doc_id')}] (Tier {d.get('reliability_tier')}, Date: {d.get('pub_date')}): {d.get('title')}\n{d.get('content')}"
                for d in evidence["documents"]
            ]) if evidence["documents"] else "No direct documents found."

            trade_text = "\n\n".join([
                f"Table {t.get('table_id')}: Baseline Avg = {t.get('baseline_average')}, Post-Event Avg = {t.get('comparison_average')}, Increase/Change = {t.get('percentage_change')}%. Rows cited: {t.get('citations')}"
                for t in evidence["trade_calculations"]
            ]) if evidence["trade_calculations"] else "No trade table calculations found."

            prompt = LOKI_CLAIM_GENERATION_PROMPT.format(
                question=case.question,
                as_of=str(case.as_of),
                scope=case.scope.model_dump_json() if case.scope else "N/A",
                evidence_text=docs_text,
                trade_text=trade_text,
                memory_context=memory_context
            )

            result: LokiRound1Output = self.client.chat.completions.create(
                model="grok-beta",
                response_model=LokiRound1Output,
                messages=[
                    {"role": "system", "content": LOKI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )

            for c in result.claims:
                c.agent = "loki"

            current_run.claims.extend(result.claims)

            return {
                "agent": "loki",
                "round": 1,
                "action": "claims_submitted",
                "claims": [c.model_dump() for c in result.claims]
            }

        # -------------------------------------------------------------
        # ROUND 2: CROSS-EXAMINATION (ATTACKS & DEFENCES)
        # -------------------------------------------------------------
        attacked_topic = case.question
        new_docs = self.tools.gather_defence_evidence(case, attacked_topic=attacked_topic)
        new_docs_text = "\n\n".join([
            f"[{d.get('doc_id')}] (Tier {d.get('reliability_tier')}): {d.get('title')} - {d.get('content')}"
            for d in new_docs
        ]) if new_docs else "No additional documents found."

        opponent_claims = [c.model_dump() for c in thor_claims]
        opponent_attacks = [a.model_dump() for a in thor_attacks]

        prompt = LOKI_CROSS_EXAMINATION_PROMPT.format(
            question=case.question,
            as_of=str(case.as_of),
            opponent_claims=opponent_claims,
            opponent_attacks=opponent_attacks,
            new_evidence_text=new_docs_text
        )

        result: LokiRound2Output = self.client.chat.completions.create(
            model="grok-beta",
            response_model=LokiRound2Output,
            messages=[
                {"role": "system", "content": LOKI_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )

        for a in result.attacks:
            a.from_agent = "loki"

        current_run.attacks.extend(result.attacks)
        current_run.defences.extend(result.defences)

        return {
            "agent": "loki",
            "round": 2,
            "action": "cross_examination_submitted",
            "attacks": [a.model_dump() for a in result.attacks],
            "defences": [d.model_dump() for d in result.defences]
        }
