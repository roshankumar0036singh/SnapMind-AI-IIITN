"""
src/agents/odin/agent.py
========================
Odin — The Allfather and Impartial Supreme Court Judge.

Orchestrates the complete judicial evaluation pipeline:
  1. Reads Case File blackboard state and recalls judicial memory precedents.
  2. Adjudicates 100% of claims, verifying citations, Simulated Clock, and math (FR4.1).
  3. Classifies findings (Established, Contested, Conceded) and synthesizes calibrated ranges (FR4.2 & FR8).
  4. Evaluates evidence sufficiency: issues 'send_back' with missing categories or approves sufficiency (FR4.3).
  5. If sufficient: compiles final executive briefing from rulings only (FR4.4).
  6. Exports reproducible Open Knowledge Format (OKF) deliverables bundle via CaseExporter (NFR6).
  7. Writes durable judicial lessons and precedents to private memory (FR6).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.agents.odin.adjudicator import OdinAdjudicator
from src.agents.odin.classifier import OdinClassifier
from src.agents.odin.sufficiency import OdinSufficiencyChecker
from src.agents.odin.briefing import OdinBriefingGenerator
from src.engine.case_exporter import CaseExporter
from src.schemas.case_file import CaseFile, RunRecord, CaseStatus
from src.tools.citation_tools import get_citation_validator, CitationValidator
from src.tools.odin_tools import (
    odin_read_memory,
    odin_write_memory,
    record_event,
)


class OdinJudge:
    """
    Main Odin Judicial Agent orchestrating Phases 1 through 5.
    """

    def __init__(
        self,
        citation_validator: Optional[CitationValidator] = None,
        output_base_dir: Optional[Path] = None,
    ):
        self.validator = citation_validator or get_citation_validator()
        self.adjudicator = OdinAdjudicator(citation_validator=self.validator)
        self.classifier = OdinClassifier()
        self.sufficiency_checker = OdinSufficiencyChecker()
        self.briefing_generator = OdinBriefingGenerator(citation_validator=self.validator)
        self.output_base_dir = output_base_dir

    def evaluate_case(
        self,
        case_file: CaseFile,
        run_no: Optional[int] = None,
    ) -> Tuple[CaseFile, Dict[str, Any]]:
        """
        Execute judicial adjudication over the current trial run.
        """
        if not case_file.runs:
            raise ValueError(f"Case {case_file.case_id} contains no trial runs to adjudicate.")

        # Identify active run
        if run_no is not None:
            matching_runs = [r for r in case_file.runs if r.run_no == run_no]
            if not matching_runs:
                raise ValueError(f"Run {run_no} not found in case {case_file.case_id}.")
            active_run = matching_runs[0]
        else:
            active_run = case_file.runs[-1]

        # 1. Recall judicial memory precedents
        try:
            precedents = odin_read_memory(
                query=f"precedents for {case_file.question}",
                case_id=case_file.case_id,
                run_no=active_run.run_no,
            )
        except Exception:
            precedents = []

        # 2. Phase 2: Adjudicate all claims (FR4.1)
        rulings = self.adjudicator.adjudicate_claims(
            claims=active_run.claims,
            attacks=active_run.attacks,
            defences=active_run.defences,
            as_of=case_file.as_of,
            event_id=case_file.scope.event_id if case_file.scope else None,
            run_no=active_run.run_no,
        )
        active_run.rulings = rulings

        # 3. Phase 3: Classify findings & synthesize ranges (FR4.2 & FR8)
        classification = self.classifier.classify_findings(rulings=rulings)
        active_run.classification = classification

        ranges = self.classifier.synthesize_ranges(
            claims=active_run.claims,
            rulings=rulings,
            scope=case_file.scope,
        )
        active_run.ranges = ranges

        # 4. Phase 4: Evaluate sufficiency (FR4.3)
        sufficiency_status, missing_categories = self.sufficiency_checker.evaluate_sufficiency(
            case_file=case_file,
            run_record=active_run,
        )
        active_run.sufficiency = sufficiency_status
        active_run.missing = missing_categories

        result_summary: Dict[str, Any] = {
            "case_id": case_file.case_id,
            "run_no": active_run.run_no,
            "rulings_count": len(rulings),
            "sufficiency": sufficiency_status,
            "missing": missing_categories,
        }

        # 5. Handle Insufficient Evidence vs Briefing Approval
        # NOTE: Odin records the finding but does NOT decide to continue the debate.
        # The runner (trial_workflow.py) owns that decision based on budget state.
        if sufficiency_status == "insufficient":
            # Record audit event
            record_event(
                case_id=case_file.case_id,
                event_type="odin_insufficient_evidence",
                agent="odin",
                run_no=active_run.run_no,
                details={
                    "missing": missing_categories,
                    "rulings_count": len(rulings),
                    "ranges_count": len(ranges),
                },
            )

            # Persist durable lesson to private memory
            try:
                odin_write_memory(
                    memory_type="sufficiency_standard",
                    content=f"Run {active_run.run_no} sent back. Missing categories: {missing_categories}",
                    basis_refs=[r.ruling_id for r in rulings[:5]],
                    run_no=active_run.run_no,
                    case_id=case_file.case_id,
                )
            except Exception:
                pass

            result_summary["action"] = "insufficient"
            return case_file, result_summary

        # 6. Phase 5: Evidence is sufficient -> compile final briefing & export deliverables
        briefing_text = self.briefing_generator.generate_briefing(
            case_file=case_file,
            run_record=active_run,
        )
        case_file.final_briefing = briefing_text
        case_file.status = CaseStatus.CLOSED

        # Export complete deliverables bundle in OKF format
        bundle_paths = CaseExporter.export_case_bundle(
            case_file=case_file,
            output_base_dir=self.output_base_dir,
            briefing_text=briefing_text,
        )
        result_summary["action"] = "briefing_complete"
        result_summary["export_bundle"] = {k: str(v) for k, v in bundle_paths.items()}

        # Record audit event
        record_event(
            case_id=case_file.case_id,
            event_type="odin_briefing_completed",
            agent="odin",
            run_no=active_run.run_no,
            details={
                "status": "closed",
                "established_count": len(classification.established),
                "contested_count": len(classification.contested),
                "conceded_count": len(classification.conceded),
                "export_bundle": {k: str(v) for k, v in bundle_paths.items()},
            },
        )

        # Write durable ruling precedent to private memory
        try:
            odin_write_memory(
                memory_type="ruling_precedent",
                content=(
                    f"Completed trial for {case_file.case_id}. "
                    f"Established: {len(classification.established)}, "
                    f"Contested: {len(classification.contested)}, "
                    f"Conceded: {len(classification.conceded)}."
                ),
                basis_refs=[r.ruling_id for r in rulings[:5]],
                run_no=active_run.run_no,
                case_id=case_file.case_id,
            )
        except Exception:
            pass

        return case_file, result_summary
