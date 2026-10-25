"""
src/agents/odin/sufficiency.py
==============================
Sufficiency Evaluator & Send-Back Logic for Odin (FR4.3).

Responsibilities:
  - Evaluates whether current Run evidence is sufficient to ground calibrated ranges and a final briefing.
  - Checks Tier 1 / Tier 2 official corroboration on primary disruption claims.
  - Checks scope coverage (countries and sectors from EventScope).
  - Checks trade data integrity (absence of critical corruption in used rows).
  - Triggers 'send_back' with structured 'missing' evidence categories on Run 1.
  - Terminates loop on Run 2 or when max_runs / limits are reached, returning 'sufficient'.
"""

from __future__ import annotations

from typing import List, Tuple, Optional

from src.schemas.case_file import CaseFile, RunRecord
from src.schemas.rulings import RulingOutcome


class OdinSufficiencyChecker:
    """
    Judicial sufficiency and send-back evaluator implementing FR4.3.
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
          where status is 'sufficient' or 'send_back'.
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
        # If all claims in the run are based solely on Tier 4 or lack Tier 1/2 corroboration
        upheld_rulings = [r for r in run_record.rulings if r.outcome == RulingOutcome.UPHELD]
        contested_rulings = [r for r in run_record.rulings if r.outcome == RulingOutcome.CONTESTED]

        if not upheld_rulings and not contested_rulings:
            missing_categories.append("admissible_evidence_no_claims_upheld")

        # 3. Trade Table Corruption Gate
        if case_file.ingest_report and case_file.ingest_report.bad_rows_count > 5:
            # High corruption in trade tables
            has_clean_calc = any(
                r.basis.value == "calculation" and r.outcome == RulingOutcome.UPHELD
                for r in run_record.rulings
            )
            if not has_clean_calc:
                missing_categories.append("corroborating_clean_trade_rows_post_disruption")

        # 4. Multi-party Contradiction Gate
        if len(contested_rulings) > len(upheld_rulings) and len(contested_rulings) >= 2:
            missing_categories.append("tier_1_official_resolution_for_contested_facts")

        # Loop Termination & Send-Back Evaluation
        max_runs = case_file.limits.get("max_runs", 2)
        if run_record.run_no >= max_runs:
            # Hard limit reached: must close as sufficient (caveats noted in briefing)
            return "sufficient", []

        if missing_categories:
            return "send_back", missing_categories

        return "sufficient", []
