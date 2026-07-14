from fastapi import APIRouter, HTTPException
from typing import Optional
from app import database as db
from app.models import InteractionFormIn, InteractionUpdateIn, FollowupIn, SummaryPreviewIn
from app.agent.tools import (
    log_interaction_tool,
    edit_interaction_tool,
    schedule_followup_tool,
    generate_call_prep_summary_tool,
)
from app.agent.llm import summarize_interaction

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.get("")
def list_interactions(hcp_id: Optional[int] = None):
    return db.list_interactions(hcp_id=hcp_id)


@router.get("/{interaction_id}")
def get_interaction(interaction_id: int):
    record = db.get_interaction(interaction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return record


@router.post("")
def log_interaction(payload: InteractionFormIn):
    """
    Used by the STRUCTURED FORM path of the Log Interaction screen. Invokes
    the exact same `log_interaction` LangGraph tool the chat path uses, so
    form-mode and chat-mode always produce identical record shapes.
    """
    data = payload.model_dump()
    if data.get("samples_distributed"):
        data["samples_distributed"] = [
            s if isinstance(s, dict) else s.model_dump() for s in payload.samples_distributed
        ]
    return log_interaction_tool.invoke(data)


@router.post("/preview-summary")
def preview_summary(payload: SummaryPreviewIn):
    """
    Powers the form's "Summarize from Voice Note" button: runs the same LLM
    summarization step used by log_interaction, but without persisting
    anything, so the rep can preview the AI's read before submitting.
    """
    return summarize_interaction(payload.raw_notes)


@router.patch("/{interaction_id}")
def edit_interaction(interaction_id: int, payload: InteractionUpdateIn):
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = edit_interaction_tool.invoke({"interaction_id": interaction_id, "updates": updates})
    if not result:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return result


@router.delete("/{interaction_id}")
def delete_interaction(interaction_id: int):
    ok = db.delete_interaction(interaction_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return {"deleted": True}


@router.post("/followup")
def schedule_followup(payload: FollowupIn):
    result = schedule_followup_tool.invoke(payload.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return result


@router.get("/call-prep/{hcp_name}")
def call_prep(hcp_name: str):
    result = generate_call_prep_summary_tool.invoke({"hcp_name": hcp_name})
    if not result:
        raise HTTPException(status_code=404, detail="HCP not found")
    return result
