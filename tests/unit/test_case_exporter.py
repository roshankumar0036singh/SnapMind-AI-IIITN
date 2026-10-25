from datetime import date
from pathlib import Path
import json
import yaml
import pytest

from src.engine.case_exporter import CaseExporter
from src.schemas.case_file import CaseFile, EventScope, VerificationVerdict


def test_export_case_bundle(tmp_path):
    case = CaseFile(
        case_id="CASE-TEST-001",
        question="How exposed are Midgard and Tolan to the Orvan corridor closure?",
        as_of=date(2027, 1, 25),
        status="closed",
        scope=EventScope(
            event_id="EVT-ORV-01",
            event_name="Orvan Corridor Expiration",
            target_countries=["Midgard", "Tolan"],
            target_sectors=["wheat", "maize"],
            as_of_date=date(2027, 1, 25),
        ),
        verification=VerificationVerdict(
            verdict="real",
            confidence=0.98,
            reasons=["Official agricultural bulletin confirms corridor expiration."],
            supporting_docs=["ORV-0005"],
            retractions=[],
            message_to_user="Event confirmed real.",
        ),
        final_briefing="## Executive Summary\n\nMidgard faces moderate exposure with alternative overland routes available.",
    )

    events = [
        {"event_type": "heimdall_verified", "timestamp": "2027-01-25T10:00:00", "details": {"verdict": "real"}},
        {"event_type": "ruling_issued", "timestamp": "2027-01-25T10:05:00", "details": {"classification": "Established"}},
    ]

    bundle = CaseExporter.export_case_bundle(
        case_file=case,
        output_base_dir=tmp_path,
        events=events,
    )

    assert "case_file_json" in bundle
    assert "final_briefing_md" in bundle
    assert "events_log" in bundle
    assert "trap_scorecard" in bundle

    # 1. Check case_file.json
    case_json_content = bundle["case_file_json"].read_text(encoding="utf-8")
    loaded_case = CaseFile.model_validate_json(case_json_content)
    assert loaded_case.case_id == "CASE-TEST-001"
    assert loaded_case.as_of == date(2027, 1, 25)

    # 2. Check final_briefing.md in OKF format
    briefing_md = bundle["final_briefing_md"].read_text(encoding="utf-8")
    assert briefing_md.startswith("---\n")
    parts = briefing_md.split("---\n")
    frontmatter = yaml.safe_load(parts[1])
    assert frontmatter["case_id"] == "CASE-TEST-001"
    assert frontmatter["verdict"] == "real"
    assert "Midgard faces moderate exposure" in briefing_md

    # 3. Check events.log JSONL lines
    log_lines = bundle["events_log"].read_text(encoding="utf-8").strip().splitlines()
    assert len(log_lines) == 2
    evt1 = json.loads(log_lines[0])
    assert evt1["event_type"] == "heimdall_verified"

    # 4. Check trap_scorecard.json
    scorecard = json.loads(bundle["trap_scorecard"].read_text(encoding="utf-8"))
    assert scorecard["case_id"] == "CASE-TEST-001"
    assert "traps_neutralized" in scorecard
