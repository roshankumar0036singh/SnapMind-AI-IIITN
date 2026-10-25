import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import yaml

from src.schemas.case_file import CaseFile
from src.schemas.rulings import Ruling


class CaseExporter:
    """
    Serializes a completed trial into a reproducible, self-contained OKF deliverables bundle.
    Fulfills CONTEXT_UPDATED.md Section 5 and Section 7.
    Outputs:
    - saved_cases/<case_id>/case_file.json
    - saved_cases/<case_id>/final_briefing.md (OKF Markdown with YAML frontmatter)
    - saved_cases/<case_id>/events.log (JSONL audit trace)
    - saved_cases/<case_id>/trap_scorecard.json
    """

    DEFAULT_BASE_DIR = Path("saved_cases")

    @classmethod
    def export_case_bundle(
        cls,
        case_file: CaseFile,
        output_base_dir: Optional[Path] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        briefing_text: Optional[str] = None,
    ) -> Dict[str, Path]:
        """
        Exports the complete case bundle into saved_cases/<case_id>/.
        """
        base_dir = Path(output_base_dir or cls.DEFAULT_BASE_DIR)
        case_dir = base_dir / case_file.case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        bundle_paths: Dict[str, Path] = {}

        # 1. Export case_file.json
        case_json_path = case_dir / "case_file.json"
        case_json_content = case_file.model_dump_json(indent=2)
        case_json_path.write_text(case_json_content, encoding="utf-8")
        bundle_paths["case_file_json"] = case_json_path

        # 2. Export final_briefing.md in OKF format
        briefing_body = (
            briefing_text
            or getattr(case_file, "final_briefing", None)
            or getattr(case_file, "briefing", None)
            or "# Executive Briefing\n\nNo briefing recorded."
        )

        from src.ingestion.okf_converter import OKFConverter
        import re

        # Extract cited references from briefing body and format as OKF wiki-links [[REF]]
        found_citations = re.findall(r"\[([A-Z0-9]+-[A-Z0-9]+(?:#P\d+|#\d+)?)\]", briefing_body, re.IGNORECASE)
        okf_links = [
            f"[[{c}]]" for c in dict.fromkeys(found_citations)
            if c.upper() not in ("LOW, HIGH", "UPHELD", "REJECTED", "CONCEDED", "CONTESTED")
        ]
        # Also include any direct [[REF]] links present
        okf_links = list(dict.fromkeys(okf_links + OKFConverter.extract_wiki_links(briefing_body)))

        frontmatter = {
            "case_id": case_file.case_id,
            "question": case_file.question,
            "as_of": case_file.as_of.isoformat() if hasattr(case_file.as_of, "isoformat") else str(case_file.as_of),
            "status": str(case_file.status),
            "verdict": getattr(case_file.verification.verdict, "value", str(case_file.verification.verdict)) if case_file.verification else "unknown",
            "total_runs": len(case_file.runs),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "links": okf_links,
        }
        yaml_header = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False).strip()
        briefing_okf_content = f"---\n{yaml_header}\n---\n\n{briefing_body.strip()}\n"

        briefing_path = case_dir / "final_briefing.md"
        briefing_path.write_text(briefing_okf_content, encoding="utf-8")
        bundle_paths["final_briefing_md"] = briefing_path

        # 3. Export events.log (JSONL audit trace)
        events_path = case_dir / "events.log"
        event_records = events or []
        lines = [json.dumps(evt, default=str) for evt in event_records]
        events_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        bundle_paths["events_log"] = events_path

        # 4. Export trap_scorecard.json
        ingest_report = case_file.ingest_report
        scorecard = {
            "case_id": case_file.case_id,
            "as_of_date": str(case_file.as_of),
            "event_verdict": str(case_file.verification.verdict) if case_file.verification else "unverified",
            "traps_neutralized": {
                "files_damaged": len(ingest_report.files_damaged) if ingest_report else 0,
                "files_duplicated": len(ingest_report.files_duplicated) if ingest_report else 0,
                "files_injection_flagged": len(ingest_report.files_injection_flagged) if ingest_report else 0,
                "bad_rows_detected": ingest_report.bad_rows_count if ingest_report else 0,
            },
            "trial_runs_completed": len(case_file.runs),
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        scorecard_path = case_dir / "trap_scorecard.json"
        scorecard_path.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
        bundle_paths["trap_scorecard"] = scorecard_path

        # 5. Export agent memories in OKF format (Acceptance Check 9)
        memories_dir = case_dir / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        try:
            from src.supabase_client import get_supabase_admin
            from src.schemas.memory import MemoryRecord, MemoryType, MemoryScope
            db = get_supabase_admin()
            mem_res = db.table("agent_memories").select("*").execute()
            records: List[MemoryRecord] = []
            if mem_res.data:
                for mem in mem_res.data:
                    raw_refs = mem.get("basis_refs", [])
                    if isinstance(raw_refs, str):
                        try:
                            raw_refs = json.loads(raw_refs)
                        except Exception:
                            raw_refs = [raw_refs]
                    records.append(
                        MemoryRecord(
                            id=mem.get("id"),
                            agent_id=str(mem.get("agent_id") or "agent").lower(),
                            memory_type=MemoryType(mem.get("memory_type", "source_lesson")),
                            content=mem.get("content", ""),
                            scope=MemoryScope(mem.get("scope", "global")),
                            scope_value=mem.get("scope_value"),
                            confidence=float(mem.get("confidence", 1.0)),
                            status=mem.get("status", "active"),
                            created_run=int(mem.get("created_run", 1)),
                            basis_refs=raw_refs,
                        )
                    )

            # If Supabase has no records or offline, fallback to local OKF memories
            if not records:
                for agent_name in ["heimdall", "thor", "loki", "odin"]:
                    records.extend(OKFConverter.load_agent_memories_from_okf(agent_name))

            if records:
                OKFConverter.export_agent_memories_to_okf(records, output_dir=memories_dir)
            bundle_paths["memories_dir"] = memories_dir
        except Exception:
            pass

        return bundle_paths
