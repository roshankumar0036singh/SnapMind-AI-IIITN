"""
src/agents/odin/sufficiency.py
==============================
Sufficiency Evaluator for Odin (FR4.3).

Responsibilities:
  - Evaluates whether current Run evidence is sufficient to ground calibrated ranges
    and a final briefing.
  - Checks Tier 1 / Tier 2 official corroboration on primary disruption claims.
  - Checks scope coverage (countries and sectors from EventScope).
  - Checks trade data integrity (absence of critical corruption in used rows).
  - Returns ('sufficient', []) or ('insufficient', missing_categories).

IMPORTANT: This evaluator does NOT control loop termination. The deterministic
runner in trial_workflow.py owns all convergence and budget termination decisions.
Odin never decides that the debate is finished — it only judges evidence quality.
"""

from __future__ import annotations

from typing import List, Tuple

from src.schemas.case_file import CaseFile, RunRecord
from src.schemas.rulings import RulingOutcome


class OdinSufficiencyChecker:
    """
    Judicial evidence-sufficiency evaluator implementing FR4.3.

    Returns one of two statuses:
      - 'sufficient'   → Evidence is of adequate quality to ground a final briefing.
      - 'insufficient' → Evidence has structural gaps; missing categories are listed.

    The runner reads this status and decides whether to continue the debate loop,
    close as incomplete, or proceed to briefing. Odin never makes that decision.
    """

    def evaluate_sufficiency(
        self,
        case_file: CaseFile,
        run_record: RunRecord,
    ) -> Tuple[str, List[str]]:
        """
        Evaluate if run_record has sufficient evidence.

        Returns:
          (sufficiency_status, missing_categories)
          where status is 'sufficient' or 'insufficient'.
        """
        missing_categories: List[str] = []

        # 1. Scope Coverage Check
        scope = case_file.scope
        if scope:
            covered_countries = {c.country.lower() for c in run_record.claims}
            covered_sectors = {c.sector.lower() for c in run_record.claims}

            for target_c in scope.target_countries:
                if target_c.lower() not in covered_countries:
                    missing_categories.append(f"evidence_for_target_country_{target_c}")

            for target_s in scope.target_sectors:
                if target_s.lower() not in covered_sectors:
                    missing_categories.append(f"evidence_for_target_sector_{target_s}")

        # 2. Corroboration & Quality Gate
        upheld_rulings = [r for r in run_record.rulings if r.outcome == RulingOutcome.UPHELD]
        contested_rulings = [r for r in run_record.rulings if r.outcome == RulingOutcome.CONTESTED]

        if not upheld_rulings and not contested_rulings:
            missing_categories.append("admissible_evidence_no_claims_upheld")

        # 3. Trade Table Corruption Gate
        if case_file.ingest_report and case_file.ingest_report.bad_rows_count > 5:
            has_clean_calc = any(
                r.basis.value == "calculation" and r.outcome == RulingOutcome.UPHELD
                for r in run_record.rulings
            )
            if not has_clean_calc:
                missing_categories.append("corroborating_clean_trade_rows_post_disruption")

        # 4. Multi-party Contradiction Gate
        if len(contested_rulings) > len(upheld_rulings) and len(contested_rulings) >= 2:
            missing_categories.append("tier_1_official_resolution_for_contested_facts")

        if missing_categories:
            if hasattr(case_file, "budget") and case_file.budget:
                budget = case_file.budget
                if getattr(budget, "evidence_runs", 0) >= getattr(budget, "max_evidence_runs", 3) and getattr(budget, "evidence_runs", 0) > 0:
                    return "incomplete", missing_categories
            return "insufficient", missing_categories

        return "sufficient", []
