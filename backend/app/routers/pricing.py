"""Pricing Pipeline Router — REST endpoints for the multi-agent pricing workflow."""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.pricing_orchestrator import (
    get_run_results,
    get_run_status,
    start_pricing_pipeline,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/pricing/start")
async def start_pricing(file: UploadFile = File(...)):
    """Upload a Pantheon/gala XML file and start the pricing pipeline.

    Returns the run_id to poll for status and results.
    """
    if not file.filename or not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="Only XML files accepted")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    # Basic XML validation
    if not file_bytes.lstrip().startswith((b"<?xml", b"<")):
        raise HTTPException(status_code=400, detail="File does not appear to be valid XML")

    run_id = await start_pricing_pipeline(file_bytes, file.filename)
    return {"run_id": run_id, "status": "started"}


@router.get("/pricing/{run_id}/status")
async def pricing_status(run_id: str):
    """Get the current stage and progress of a pricing pipeline run."""
    state = get_run_status(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": state["run_id"],
        "stage": state["stage"],
        "progress": state.get("progress", 0),
        "started_at": state.get("started_at"),
        "finished_at": state.get("finished_at"),
        "error": state.get("error"),
    }


@router.get("/pricing/{run_id}/results")
async def pricing_results(run_id: str):
    """Get the full results of a completed pricing pipeline run.

    Only available when the run has reached the DONE stage.
    """
    state = get_run_status(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")

    if state["stage"] == "error":
        raise HTTPException(
            status_code=500,
            detail=f"Run failed: {state.get('error', 'unknown error')}",
        )

    if state["stage"] != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Run not complete, current stage: {state['stage']}",
        )

    return get_run_results(run_id)
