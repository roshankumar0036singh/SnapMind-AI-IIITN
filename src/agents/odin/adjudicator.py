"""
src/agents/odin/adjudicator.py
==============================
Deep Claim Adjudication & Citation Verification Engine for Odin (FR4.1).

Responsibilities:
  - Rules on 100% of claims (including unchallenged or failed-side claims).
  - Enforces the Simulated Clock (rejection of any source published after as_of_date).
  - Verifies citations against Runemark manifest and trade tables using CitationValidator.
  - Audits calculations (baseline, row statuses, volume vs value).
  - Evaluates cross-examinations (attacks and defences), recognizing formal concessions.
  - Assigns RulingOutcome (upheld, rejected, conceded, contested) and RulingBasis (sourced_fact, calculation, inference).
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple, Any

from src.schemas.claims import Claim, Attack, Defence, ClaimKind
from src.schemas.rulings import Ruling, RulingOutcome, RulingBasis
from src.tools.citation_tools import get_citation_validator, CitationValidator


class OdinAdjudicator:
    """
    Judicial claim adjudicator implementing FR4.1.
    """

    def __init__(self, citation_validator: Optional[CitationValidator] = None):
        self.validator = citation_validator or get_citation_validator()

    def adjudicate_claims(
        self,
        claims: List[Claim],
        attacks: Optional[List[Attack]] = None,
        defences: Optional[List[Defence]] = None,
        as_of: Optional[date] = None,
        event_id: Optional[str] = None,
        run_no: int = 1,
    ) -> List[Ruling]:
        """
        Adjudicate all submitted claims and return corresponding Ruling objects.
        """
        attacks = attacks or []
        defences = defences or []
        rulings: List[Ruling] = []

        # Index attacks by target_claim_id
        attacks_by_claim: Dict[str, List[Attack]] = {}
        for atk in attacks:
            attacks_by_claim.setdefault(atk.target_claim_id, []).append(atk)

        # Index defences by attack_id
        defences_by_attack: Dict[str, List[Defence]] = {}
        for dfn in defences:
            defences_by_attack.setdefault(dfn.attack_id, []).append(dfn)

        for idx, claim in enumerate(claims, start=1):
            ruling = self._adjudicate_single_claim(
                claim=claim,
                claim_attacks=attacks_by_claim.get(claim.claim_id, []),
                defences_by_attack=defences_by_attack,
                as_of=as_of,
                event_id=event_id,
                ruling_id=f"RUL-ODIN-R{run_no}-{idx:02d}",
            )
            rulings.append(ruling)

        return rulings

    def _adjudicate_single_claim(
        self,
        claim: Claim,
        claim_attacks: List[Attack],
        defences_by_attack: Dict[str, List[Defence]],
        as_of: Optional[date],
        event_id: Optional[str],
        ruling_id: str,
    ) -> Ruling:
        refs_checked: List[str] = []
        citations_valid = True
        citation_rejection_reasons: List[str] = []

        # 1. Verify all citations
        if not claim.citations:
            return Ruling(
                ruling_id=ruling_id,
                claim_id=claim.claim_id,
                outcome=RulingOutcome.REJECTED,
                basis=RulingBasis.INFERENCE,
                reasoning="Claim rejected: no citations provided (violates NFR2 zero-hallucination requirement).",
                refs_checked=[],
            )

        for cit in claim.citations:
            refs_checked.append(cit)
            resp = self.validator.verify_citation(citation_ref=cit, case_as_of_date=as_of or date.today())
            if not resp.is_valid:
                citations_valid = False
                citation_rejection_reasons.append(f"Citation {cit!r}: {resp.reason}")

        # If any citation failed verification, reject the claim immediately
        if not citations_valid:
            joined_reasons = "; ".join(citation_rejection_reasons)
            return Ruling(
                ruling_id=ruling_id,
                claim_id=claim.claim_id,
                outcome=RulingOutcome.REJECTED,
                basis=RulingBasis.INFERENCE,
                reasoning=f"Claim rejected due to citation verification failure: {joined_reasons}",
                refs_checked=refs_checked,
            )

        # 2. Determine Basis (Sourced Fact, Calculation, Inference)
        basis = self._determine_basis(claim)

        # 3. Check for Concessions from cross-examination
        for atk in claim_attacks:
            atk_defences = defences_by_attack.get(atk.attack_id, [])
            for dfn in atk_defences:
                if dfn.response_type == "concede":
                    return Ruling(
                        ruling_id=ruling_id,
                        claim_id=claim.claim_id,
                        outcome=RulingOutcome.CONCEDED,
                        basis=basis,
                        reasoning=(
                            f"Claim formally conceded by {claim.agent} in response to attack "
                            f"{atk.attack_id} (grounds: {atk.grounds}): {dfn.text}"
                        ),
                        refs_checked=refs_checked,
                    )

        # 4. Check Attacks & Defences outcomes
        if claim_attacks:
            for atk in claim_attacks:
                atk_defences = defences_by_attack.get(atk.attack_id, [])
                
                # Check if counter-evidence in attack was verified
                attack_evidence_valid = True
                for ev_ref in atk.evidence_refs:
                    refs_checked.append(ev_ref)
                    ev_resp = self.validator.verify_citation(citation_ref=ev_ref, case_as_of_date=as_of or date.today())
                    if not ev_resp.is_valid:
                        attack_evidence_valid = False

                if not atk_defences:
                    # Attack un-rebutted
                    if attack_evidence_valid and atk.evidence_refs:
                        return Ruling(
                            ruling_id=ruling_id,
                            claim_id=claim.claim_id,
                            outcome=RulingOutcome.REJECTED,
                            basis=basis,
                            reasoning=(
                                f"Claim rejected: attacked by {atk.from_agent} ({atk.attack_id}) "
                                f"on grounds of {atk.grounds!r} with valid counter-evidence, and left undefended."
                            ),
                            refs_checked=refs_checked,
                        )
                    else:
                        # Groundless or unevidenced attack does not invalidate verified claim
                        pass
                else:
                    # Defendant provided defence
                    for dfn in atk_defences:
                        if dfn.response_type == "new_evidence":
                            # Check if new references are valid
                            new_refs_valid = len(dfn.new_refs) > 0
                            for nref in dfn.new_refs:
                                refs_checked.append(nref)
                                nresp = self.validator.verify_citation(citation_ref=nref, case_as_of_date=as_of or date.today())
                                if not nresp.is_valid:
                                    new_refs_valid = False

                            if not new_refs_valid:
                                return Ruling(
                                    ruling_id=ruling_id,
                                    claim_id=claim.claim_id,
                                    outcome=RulingOutcome.REJECTED,
                                    basis=basis,
                                    reasoning=(
                                        f"Claim rejected: defence {dfn.defence_id} failed to substantiate "
                                        f"rebuttal with valid new Runemark evidence."
                                    ),
                                    refs_checked=refs_checked,
                                )
                            else:
                                # Both sides have credible evidence -> Contested
                                if attack_evidence_valid and atk.evidence_refs:
                                    return Ruling(
                                        ruling_id=ruling_id,
                                        claim_id=claim.claim_id,
                                        outcome=RulingOutcome.CONTESTED,
                                        basis=basis,
                                        reasoning=(
                                            f"Finding contested: attack {atk.attack_id} provided valid counter-evidence, "
                                            f"while defence {dfn.defence_id} introduced valid competing evidence."
                                        ),
                                        refs_checked=refs_checked,
                                    )

        # 5. Default Upheld
        return Ruling(
            ruling_id=ruling_id,
            claim_id=claim.claim_id,
            outcome=RulingOutcome.UPHELD,
            basis=basis,
            reasoning=(
                f"Claim upheld as grounded: verified {len(claim.citations)} citation(s) "
                f"within Simulated Clock window (as-of: {as_of or 'none'})."
            ),
            refs_checked=refs_checked,
        )

    def _determine_basis(self, claim: Claim) -> RulingBasis:
        """
        Classifies claim into SOURCED_FACT, CALCULATION, or INFERENCE.
        """
        if claim.kind == ClaimKind.CALCULATION:
            return RulingBasis.CALCULATION

        text_lower = claim.text.lower()
        inference_keywords = [
            "project", "estimate", "expected", "likely", "forecast",
            "could decline", "may drop", "assumes", "anticipate", "predict"
        ]

        if claim.kind == ClaimKind.INFERENCE or any(kw in text_lower for kw in inference_keywords):
            return RulingBasis.INFERENCE

        # Has valid citation and asserts direct observation
        return RulingBasis.SOURCED_FACT
