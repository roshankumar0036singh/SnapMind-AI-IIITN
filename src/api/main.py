"""
src/api/main.py
===============
FastAPI Backend Server for Trial of the Nine Realms.
Bridges the frontend dashboard to:
  1. `run_trial_pipeline()` in `src.engine.trial_workflow`
  2. `ingest_event_pack()` in `src.cli.ingest_pack`
  3. Case inspection & local deliverables in `saved_cases/`
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.engine.trial_workflow import run_trial_pipeline
from src.supabase_client import get_supabase_admin


app = FastAPI(
    title="Trial of the Nine Realms API",
    description="Multi-Agent Judicial Trial & Disruption Intelligence Pipeline",
    version="1.0.0",
)

# Enable CORS for frontend development (Vite, React, Live Server, file://)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request & Response Models
# -----------------------------------------------------------------------------
class TrialRunRequest(BaseModel):
    question: str = Field(..., description="User query or disruption investigation prompt")
    as_of: str = Field("2027-01-25", description="Simulated Clock date in YYYY-MM-DD format")
    event_id: Optional[str] = Field(None, description="Optional target event ID (e.g. E5)")


class IngestPackRequest(BaseModel):
    pack_dir: str = Field(..., description="Directory containing manifest.json and event files")
    event_id: Optional[str] = Field(None, description="Optional target event ID")


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Health check verifying API and Supabase availability."""
    db_ok = False
    try:
        db = get_supabase_admin()
        res = db.table("case_files").select("count", count="exact").limit(1).execute()
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy",
        "supabase_connected": db_ok,
        "default_clock": "2027-01-25",
    }


@app.post("/api/trial/run")
async def run_trial_endpoint(req: TrialRunRequest) -> Dict[str, Any]:
    """
    Main Frontend Trigger:
    Executes the entire end-to-end trial workflow:
      Phase 1: Heimdall Gatekeeper (validation, clock check, scope extraction)
      Phase 2: Thor & Loki Adversarial Debate (Rounds 1 & 2)
      Phase 3: Odin Supreme Judicial Review & OKF Briefing
      Export : Full reproducibility bundle saved to saved_cases/<case_id>/
    """
    try:
        result = await run_trial_pipeline(
            question=req.question,
            as_of=req.as_of,
            event_id=req.event_id,
        )

        # Serialize Pydantic case_file if present
        case_file_obj = result.get("case_file")
        serialized_case = case_file_obj.model_dump(mode="json") if hasattr(case_file_obj, "model_dump") else case_file_obj

        return {
            "case_id": result.get("case_id"),
            "status": result.get("status"),
            "verdict": result.get("verdict"),
            "confidence": result.get("confidence"),
            "reasons": result.get("reasons"),
            "wake_next": result.get("wake_next"),
            "bundle_paths": result.get("bundle_paths", {}),
            "judicial_output": result.get("judicial_output"),
            "case_file": serialized_case,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trial workflow failed: {str(e)}")


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> Dict[str, Any]:
    """Retrieves a case file either from local saved_cases/ or Supabase."""
    local_case = Path("saved_cases") / case_id / "case_file.json"
    if local_case.exists():
        import json
        return json.loads(local_case.read_text(encoding="utf-8"))

    try:
        db = get_supabase_admin()
        res = db.table("case_files").select("*").eq("case_id", case_id).single().execute()
        if res.data:
            return res.data
    except Exception:
        pass

    raise HTTPException(status_code=404, detail=f"Case {case_id} not found")


@app.post("/api/ingest/pack")
def ingest_pack_endpoint(req: IngestPackRequest) -> Dict[str, Any]:
    """Ingests a Section 4.5 Live Round Event Pack."""
    pack_path = Path(req.pack_dir)
    if not pack_path.exists() or not pack_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Pack directory not found: {req.pack_dir}")

    try:
        from src.cli.ingest_pack import ingest_event_pack
        report = ingest_event_pack(pack_dir=pack_path, event_id=req.event_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pack ingestion failed: {str(e)}")


# -----------------------------------------------------------------------------
# Mount Frontend Static Assets
# -----------------------------------------------------------------------------
frontend_dir = Path("frontend")
if frontend_dir.exists() and (frontend_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
